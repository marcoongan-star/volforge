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
  assert.match(html, /Recovery cursor/i);
  assert.match(html, /Confirmed through sequence 1/i);
  assert.match(html, /Simulate disconnect/i);
  assert.match(html, /Cursor recovery/i);
  assert.doesNotMatch(html, /Your site is taking shape|Building your site/);
});

test("labels the scenario and avoids performance claims", async () => {
  const response = await render();
  const html = await response.text();
  assert.match(html, /synthetic scenario/i);
  assert.match(html, /not evidence of a profitable strategy/i);
  assert.match(html, /not investment advice/i);
});
