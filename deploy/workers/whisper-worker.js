/**
 * Cloudflare Worker: paid transcription proxy.
 *
 * Required secrets:
 * - OPENAI_API_KEY
 * - TOKEN_SIGNING_SECRET
 */

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
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

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/api/transcribe") {
      const ok = await verifyToken(request.headers.get("Authorization"), env);
      if (!ok) return json({ error: "Unauthorized" }, 401);

      try {
        const formIn = await request.formData();
        const file = formIn.get("file");
        if (!file) return json({ error: "file missing" }, 400);
        if (!isAllowedMimeType(file.type || "")) {
          return json({ error: "Unsupported file type" }, 415);
        }
        const maxUploadBytes = parseInt(env.MAX_UPLOAD_BYTES || "25000000", 10);
        if (typeof file.size === "number" && file.size > maxUploadBytes) {
          return json({ error: `File too large (max ${maxUploadBytes} bytes)` }, 413);
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
          return json({ error: errorText || "Transcription failed" }, response.status);
        }
        const srt = await response.text();
        return json({ srt });
      } catch (error) {
        return json({ error: error.message }, 500);
      }
    }
    return json({ error: "not found" }, 404);
  }
};
