#!/usr/bin/env node
// faf-kernel oracle — scores YAML with faf-scoring-kernel (the WASM build of
// faf-rust crates/faf-kernel) so the Python parity harness can compare.
//
// Input (stdin): JSON array of YAML strings.
// Output (stdout): JSON array, one entry per input:
//   { "ok": true,  "result": <kernel score_faf JSON> }
//   { "ok": false, "error": "<kernel error message>" }   (unreadable YAML)
//
// Setup: npm i faf-scoring-kernel@3.0.0  (or set FAF_KERNEL_PATH to the package dir)

const kernel = require(process.env.FAF_KERNEL_PATH || 'faf-scoring-kernel');

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
  const docs = JSON.parse(input);
  const out = docs.map((yaml) => {
    try {
      return { ok: true, result: JSON.parse(kernel.score_faf(yaml)) };
    } catch (e) {
      return { ok: false, error: String(e && e.message ? e.message : e) };
    }
  });
  process.stdout.write(JSON.stringify({ version: kernel.sdk_version(), results: out }));
});
