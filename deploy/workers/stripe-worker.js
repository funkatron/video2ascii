/**
 * Cloudflare Worker: Stripe checkout + token minting.
 *
 * Required secrets:
 * - STRIPE_SECRET_KEY
 * - STRIPE_WEBHOOK_SECRET
 * - TOKEN_SIGNING_SECRET
 * - PRICE_ID
 */

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
}

async function createCheckoutSession(body, env) {
  const params = new URLSearchParams();
  params.set("mode", "payment");
  params.set("success_url", `${body.return_url}?paid=1`);
  params.set("cancel_url", body.return_url);
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

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/api/billing/checkout") {
      try {
        const body = await request.json();
        if (!body.return_url) return json({ error: "return_url required" }, 400);
        const checkout_url = await createCheckoutSession(body, env);
        return json({ checkout_url });
      } catch (error) {
        return json({ error: error.message }, 500);
      }
    }

    if (request.method === "POST" && url.pathname === "/api/billing/token") {
      // Lightweight token endpoint for development/CLI testing.
      const token = await mintToken(
        { tier: "paid", iat: Date.now(), exp: Date.now() + (30 * 24 * 3600 * 1000) },
        env
      );
      return json({ token });
    }

    return json({ error: "not found" }, 404);
  }
};
