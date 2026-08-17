// OPTIONAL edge function. You do NOT need this for the core build.
//
// Primary AWS connection is FastAPI (on Lambda) talking to Supabase with the
// service-role key. Use this only if you want Supabase to PUSH an event to AWS
// on a database change (for example: content changed -> tell the worker to
// re-embed) instead of the EventBridge-scheduled poll.
//
// Wire it up as a Supabase Database Webhook on the table you care about, or
// call it from a trigger via pg_net. It forwards the payload to an AWS API
// Gateway endpoint with a shared secret. For production, prefer SigV4 or IAM
// auth over a shared secret.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";

Deno.serve(async (req) => {
  const secret = Deno.env.get("AWS_PROXY_SECRET");
  const endpoint = Deno.env.get("AWS_ENDPOINT_URL");
  if (!secret || !endpoint) {
    return new Response("not configured", { status: 500 });
  }
  const payload = await req.text();
  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-kala-signature": secret, // replace with SigV4/IAM in production
    },
    body: payload,
  });
  return new Response(await res.text(), { status: res.status });
});
