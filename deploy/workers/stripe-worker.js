/**
 * Cloudflare Worker: Stripe checkout + token minting.
 *
 * Required secrets:
 * - STRIPE_SECRET_KEY
 * - TOKEN_SIGNING_SECRET
 * - PRICE_ID
 * - ALLOWED_RETURN_ORIGINS (comma separated)
 */

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
}

async function createCheckoutSession(body, env) {
  const returnUrl = new URL(body.return_url);
  const params = new URLSearchParams();
  params.set("mode", "payment");
  params.set("success_url", `${returnUrl.origin}${returnUrl.pathname}?checkout_session_id={CHECKOUT_SESSION_ID}`);
  params.set("cancel_url", `${returnUrl.origin}${returnUrl.pathname}`);
  params.set("line_items[0][price]", env.PRICE_ID);
  params.set("line_items[0][quantity]", "1");

  const response = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`,
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: params.toString()
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Stripe error: ${text}`);
  }
  const data = await response.json();
  return data.url;
}

async function hmacHex(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return Array.from(new Uint8Array(sig)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function mintToken(payload, env) {
  const value = btoa(JSON.stringify(payload));
  const sig = await hmacHex(env.TOKEN_SIGNING_SECRET, value);
  return `${value}.${sig}`;
}

function isAllowedReturnUrl(urlString, env) {
  try {
    const url = new URL(urlString);
    const allowed = (env.ALLOWED_RETURN_ORIGINS || "")
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean);
    return allowed.includes(url.origin);
  } catch {
    return false;
  }
}

async function fetchCheckoutSession(sessionId, env) {
  const response = await fetch(`https://api.stripe.com/v1/checkout/sessions/${sessionId}`, {
    method: "GET",
    headers: { Authorization: `Bearer ${env.STRIPE_SECRET_KEY}` }
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Stripe lookup failed: ${text}`);
  }
  return response.json();
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/api/billing/checkout") {
      try {
        const body = await request.json();
        if (!body.return_url) return json({ error: "return_url required" }, 400);
        if (!isAllowedReturnUrl(body.return_url, env)) {
          return json({ error: "return_url origin not allowed" }, 400);
        }
        const checkout_url = await createCheckoutSession(body, env);
        return json({ checkout_url });
      } catch (error) {
        return json({ error: error.message }, 500);
      }
    }

    if (request.method === "POST" && url.pathname === "/api/billing/exchange") {
      try {
        const body = await request.json();
        if (!body.checkout_session_id) {
          return json({ error: "checkout_session_id required" }, 400);
        }
        const session = await fetchCheckoutSession(body.checkout_session_id, env);
        if (session.payment_status !== "paid" || session.status !== "complete") {
          return json({ error: "Payment not completed" }, 402);
        }
        const token = await mintToken(
          { tier: "paid", iat: Date.now(), exp: Date.now() + (30 * 24 * 3600 * 1000), sid: session.id },
          env
        );
        return json({ token });
      } catch (error) {
        return json({ error: error.message }, 500);
      }
    }

    return json({ error: "not found" }, 404);
  }
};
