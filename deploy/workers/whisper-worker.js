/**
 * Cloudflare Worker: paid transcription proxy.
 *
 * Required secrets:
 * - OPENAI_API_KEY
 * - TOKEN_SIGNING_SECRET
 * Optional:
 * - VIDEO2ASCII_TRANSCRIBE_PROVIDER=openai|local (default openai)
 * - VIDEO2ASCII_LOCAL_TRANSCRIBE_URL (required when provider=local)
 * - VIDEO2ASCII_LOCAL_TRANSCRIBE_SECRET (optional header for local endpoint)
 */

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const CORS_ALLOW_HEADERS = "authorization, content-type";
const CORS_ALLOW_METHODS = "POST, OPTIONS";

function allowedOrigins(env) {
  const raw = env.CORS_ALLOW_ORIGINS || env.ALLOWED_RETURN_ORIGINS || "*";
  return raw
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

function resolveCorsOrigin(request, env) {
  const origin = request.headers.get("Origin");
  if (!origin) return null;
  const allowed = allowedOrigins(env);
  if (allowed.includes("*")) return "*";
  if (allowed.includes(origin)) return origin;
  return null;
}

function corsHeaders(request, env) {
  const origin = resolveCorsOrigin(request, env);
  if (!origin) return null;
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-methods": CORS_ALLOW_METHODS,
    "access-control-allow-headers": CORS_ALLOW_HEADERS,
    "access-control-max-age": "86400",
    vary: "Origin"
  };
}

function json(data, status = 200, request, env) {
  const headers = { ...JSON_HEADERS };
  const cors = corsHeaders(request, env);
  if (cors) Object.assign(headers, cors);
  return new Response(JSON.stringify(data), { status, headers });
}

function preflight(request, env) {
  const cors = corsHeaders(request, env);
  if (!cors) {
    return new Response("Origin not allowed", { status: 403, headers: JSON_HEADERS });
  }
  return new Response(null, { status: 204, headers: cors });
}

async function hmacHex(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify", "sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return Array.from(new Uint8Array(sig)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function verifyToken(authHeader, env) {
  if (!authHeader || !authHeader.startsWith("Bearer ")) return false;
  const token = authHeader.replace("Bearer ", "").trim();
  const parts = token.split(".");
  if (parts.length !== 2) return false;
  const [payloadB64, signature] = parts;
  const expected = await hmacHex(env.TOKEN_SIGNING_SECRET, payloadB64);
  if (expected !== signature) return false;
  try {
    const payload = JSON.parse(atob(payloadB64));
    return payload.exp && payload.exp > Date.now();
  } catch {
    return false;
  }
}

function isAllowedMimeType(type) {
  if (!type) return false;
  return type.startsWith("audio/") || type.startsWith("video/");
}

async function transcribeWithLocalProvider(file, env) {
  const targetUrl = env.VIDEO2ASCII_LOCAL_TRANSCRIBE_URL || "";
  if (!targetUrl) {
    throw new Error("VIDEO2ASCII_LOCAL_TRANSCRIBE_URL is required for local provider");
  }
  const formOut = new FormData();
  formOut.append("file", file, file.name || "audio_or_video");
  const headers = {};
  if (env.VIDEO2ASCII_LOCAL_TRANSCRIBE_SECRET) {
    headers["x-transcribe-secret"] = env.VIDEO2ASCII_LOCAL_TRANSCRIBE_SECRET;
  }
  const response = await fetch(targetUrl, {
    method: "POST",
    headers,
    body: formOut
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Local transcription failed");
  }
  const data = await response.json();
  if (!data.srt) {
    throw new Error("Local transcription response missing srt");
  }
  return data.srt;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return preflight(request, env);
    }
    if (request.method === "POST" && url.pathname === "/api/transcribe") {
      const ok = await verifyToken(request.headers.get("Authorization"), env);
      if (!ok) return json({ error: "Unauthorized" }, 401, request, env);

      try {
        const formIn = await request.formData();
        const file = formIn.get("file");
        if (!file) return json({ error: "file missing" }, 400, request, env);
        if (!isAllowedMimeType(file.type || "")) {
          return json({ error: "Unsupported file type" }, 415, request, env);
        }
        const maxUploadBytes = parseInt(env.MAX_UPLOAD_BYTES || "25000000", 10);
        if (typeof file.size === "number" && file.size > maxUploadBytes) {
          return json({ error: `File too large (max ${maxUploadBytes} bytes)` }, 413, request, env);
        }

        const provider = (env.VIDEO2ASCII_TRANSCRIBE_PROVIDER || "openai").toLowerCase();
        if (provider === "local") {
          const srt = await transcribeWithLocalProvider(file, env);
          return json({ srt }, 200, request, env);
        }

        const formOut = new FormData();
        formOut.append("file", file, file.name || "audio_or_video");
        formOut.append("model", "gpt-4o-mini-transcribe");
        formOut.append("response_format", "srt");

        const response = await fetch("https://api.openai.com/v1/audio/transcriptions", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${env.OPENAI_API_KEY}`
          },
          body: formOut
        });
        if (!response.ok) {
          const errorText = await response.text();
          return json({ error: errorText || "Transcription failed" }, response.status, request, env);
        }
        const srt = await response.text();
        return json({ srt }, 200, request, env);
      } catch (error) {
        return json({ error: error.message }, 500, request, env);
      }
    }
    return json({ error: "not found" }, 404, request, env);
  }
};
