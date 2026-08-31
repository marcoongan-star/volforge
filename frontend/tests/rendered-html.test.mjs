import assert from "node:assert/strict";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the VolForge learning lab", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>VolForge — Options Market-Making Lab<\/title>/i);
  assert.match(html, /Can you quote risk/);
  assert.match(html, /Step →/);
  assert.match(html, /Server-owned event log/i);
  assert.match(html, /P&amp;L bridge/);
  assert.match(html, /Synthetic inputs only/);
  assert.match(html, /WebSocket notify · HTTP recover/i);
  assert.match(html, /Confirmed through sequence 1/i);
  assert.match(html, /Simulate disconnect/i);
  assert.match(html, /WebSocket \+ cursor recovery/i);
  assert.match(html, /500 PAIRED SYNTHETIC PATHS/i);
  assert.match(html, /EXPECTED SHORTFALL/i);
  assert.match(html, /Directional outperformed on 32\.60% of paths/i);
  assert.match(html, /95% interval/i);
  assert.match(html, /Paired effect: 0\.0070/i);
  assert.match(html, /interval crosses zero/i);
  assert.match(html, /Does the answer survive volatility/i);
  assert.match(html, /Conclusion changes/i);
  assert.match(html, /Maker advantage/i);
  assert.match(html, /Directional advantage/i);
  assert.match(html, /Did pairing improve precision/i);
  assert.match(html, /UNPAIRED SE/i);
  assert.match(html, /1\.0027×/i);
  assert.match(html, /0\.27%/i);
  assert.match(html, /How many paths are enough/i);
  assert.match(html, /CURRENT MARGIN/i);
  assert.match(html, /655/);
  assert.match(html, /ADDITIONAL/i);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/);
});

test("labels the scenario and avoids performance claims", async () => {
  const response = await render();
  const html = await response.text();
  assert.match(html, /synthetic scenario/i);
  assert.match(html, /not evidence of a profitable strategy/i);
  assert.match(html, /not investment advice/i);
  assert.match(html, /not expected live performance/i);
});
