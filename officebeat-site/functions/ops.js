// Cloudflare Pages Function — serves the ops dashboard backend at /ops
// on officebeatllc.com itself (same origin as ops.html — no separate worker, no CORS).
//
// Requires, in the officebeat Pages project settings:
//   - KV namespace binding: variable name  OPS_KV
//   - Environment variable (encrypt it):    OPS_KEY  = your long admin key
//
// GET  /ops   -> returns stored JSON (or null)
// PUT  /ops   -> stores JSON body
// Both require header  X-Ops-Key  matching OPS_KEY.

export async function onRequest(context) {
  const { request, env } = context;

  if (!env.OPS_KEY || request.headers.get("X-Ops-Key") !== env.OPS_KEY) {
    return new Response("unauthorized", { status: 401 });
  }

  if (request.method === "GET") {
    const data = await env.OPS_KV.get("opsdata");
    return new Response(data || "null", {
      headers: { "Content-Type": "application/json" },
    });
  }

  if (request.method === "PUT") {
    const body = await request.text();
    if (body.length > 2_000_000)
      return new Response("too large", { status: 413 });
    try { JSON.parse(body); } catch {
      return new Response("invalid json", { status: 400 });
    }
    await env.OPS_KV.put("opsdata", body);
    return new Response("ok");
  }

  return new Response("method not allowed", { status: 405 });
}
