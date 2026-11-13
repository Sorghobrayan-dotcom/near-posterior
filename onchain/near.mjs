// NEAR client for the forecast registry, Node standard library only (no npm package).
// Signs and sends transactions with node:crypto (ed25519) and the public JSON-RPC.
//
//   node onchain/near.mjs create <account>         new testnet account, key in ~/.near-credentials
//   node onchain/near.mjs deploy <account> <wasm>  deploy the registry contract
//   node onchain/near.mjs commit <account>         commit the registered forecasts
//   node onchain/near.mjs call <signer> <contract> <method> [args]
//   node onchain/near.mjs view <account> <method> [args]
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const NET = process.env.NEAR_NETWORK || "testnet";
const RPC = process.env.NEAR_RPC || (NET === "mainnet" ? "https://rpc.mainnet.fastnear.com" : "https://rpc.testnet.fastnear.com");
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

function b58enc(buf) {
  let n = BigInt("0x" + (Buffer.from(buf).toString("hex") || "0")), s = "";
  while (n > 0n) { s = B58[Number(n % 58n)] + s; n /= 58n; }
  for (const b of buf) { if (b !== 0) break; s = "1" + s; }
  return s;
}
function b58dec(s) {
  let n = 0n;
  for (const c of s) n = n * 58n + BigInt(B58.indexOf(c));
  let hex = n.toString(16); if (hex.length % 2) hex = "0" + hex;
  const lead = s.match(/^1*/)[0].length;
  return Buffer.concat([Buffer.alloc(lead), Buffer.from(n === 0n ? "" : hex, "hex")]);
}

async function rpc(method, params) {
  const r = await fetch(RPC, { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: "np", method, params }) });
  const j = await r.json();
  if (j.error) throw new Error(JSON.stringify(j.error));
  return j.result;
}

const credFile = (acct) => path.join(os.homedir(), ".near-credentials", NET, acct + ".json");
function loadKey(acct) {
  const c = JSON.parse(fs.readFileSync(credFile(acct), "utf8"));
  const sk = b58dec(c.private_key.split(":")[1]);
  const seed = sk.subarray(0, 32);
  const der = Buffer.concat([Buffer.from("302e020100300506032b657004220420", "hex"), seed]);
  return { pub: b58dec(c.public_key.split(":")[1]), priv: crypto.createPrivateKey({ key: der, format: "der", type: "pkcs8" }) };
}

// Borsh
const u8 = (v) => Buffer.from([v]);
const u32 = (v) => { const b = Buffer.alloc(4); b.writeUInt32LE(v); return b; };
const u64 = (v) => { const b = Buffer.alloc(8); b.writeBigUInt64LE(BigInt(v)); return b; };
const u128 = (v) => { const b = Buffer.alloc(16); let n = BigInt(v); for (let i = 0; i < 16; i++) { b[i] = Number(n & 255n); n >>= 8n; } return b; };
const bytes = (b) => Buffer.concat([u32(b.length), Buffer.from(b)]);
const str = (s) => bytes(Buffer.from(s, "utf8"));

async function send(acct, receiver, actions) {
  const k = loadKey(acct);
  const pk = "ed25519:" + b58enc(k.pub);
  const ak = await rpc("query", { request_type: "view_access_key", finality: "final", account_id: acct, public_key: pk });
  const tx = Buffer.concat([str(acct), u8(0), k.pub, u64(BigInt(ak.nonce) + 1n), str(receiver),
    b58dec(ak.block_hash), u32(actions.length), ...actions]);
  const sig = crypto.sign(null, crypto.createHash("sha256").update(tx).digest(), k.priv);
  const signed = Buffer.concat([tx, u8(0), sig]).toString("base64");
  const res = await rpc("send_tx", { signed_tx_base64: signed, wait_until: "FINAL" });
  const st = res.status || {};
  if (st.Failure) throw new Error(JSON.stringify(st.Failure));
  return res;
}
const deployAction = (code) => Buffer.concat([u8(1), bytes(code)]);
const callAction = (m, args, gas = 30_000_000_000_000n) => Buffer.concat([u8(2), str(m), bytes(args), u64(gas), u128(0)]);

async function view(acct, method, args = "") {
  const r = await rpc("query", { request_type: "call_function", finality: "final", account_id: acct,
    method_name: method, args_base64: Buffer.from(args).toString("base64") });
  return Buffer.from(r.result).toString("utf8");
}

const sha = (f) => crypto.createHash("sha256").update(fs.readFileSync(path.join(ROOT, f))).digest("hex");

const [cmd, acct, ...rest] = process.argv.slice(2);
if (cmd === "create") {
  if (fs.existsSync(credFile(acct))) throw new Error("key already exists: " + credFile(acct));
  const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");
  const pub = publicKey.export({ format: "der", type: "spki" }).subarray(-32);
  const seed = privateKey.export({ format: "der", type: "pkcs8" }).subarray(-32);
  const pk = "ed25519:" + b58enc(pub);
  const r = await fetch("https://helper.nearprotocol.com/account", { method: "POST",
    headers: { "content-type": "application/json" }, body: JSON.stringify({ newAccountId: acct, newAccountPublicKey: pk }) });
  if (!r.ok) throw new Error("faucet: " + r.status + " " + (await r.text()));
  fs.mkdirSync(path.dirname(credFile(acct)), { recursive: true });
  fs.writeFileSync(credFile(acct), JSON.stringify({ account_id: acct, public_key: pk,
    private_key: "ed25519:" + b58enc(Buffer.concat([seed, pub])) }), { mode: 0o600 });
  console.log("created", acct, pk, "key saved to", credFile(acct));
} else if (cmd === "deploy") {
  const res = await send(acct, acct, [deployAction(fs.readFileSync(rest[0]))]);
  console.log("deployed, tx", res.transaction.hash);
} else if (cmd === "commit") {
  const reg = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "registered_forecast.json"), "utf8"));
  const commit = execSync("git rev-parse HEAD", { cwd: ROOT }).toString().trim();
  const files = ["results/registered_forecast.json", "PREREG.md", "PREREG_2.md", "PREREG_3.md"];
  const hashes = Object.fromEntries(files.map((f) => [f, sha(f)]));
  const out = { network: NET, contract: acct, code_sha256: rest[0] ? sha(rest[0]) : null, commitments: [] };
  for (const h of Object.keys(reg.forecasts)) {
    const f = reg.forecasts[h];
    const record = JSON.stringify({ project: "near-posterior", repo: "https://github.com/Sorghobrayan-dotcom/near-posterior",
      git_commit: commit, question: `P(NEAR buybacks cover NEAR net issuance at the ${h}-month mark)`,
      h_months: Number(h), t0: reg.t0, class: reg.class, k_star: f.k_star, P: f.P, interval: f.interval,
      resolution_date: f.resolution_date, rule: reg.rule, sha256: hashes });
    const due = Math.floor(Date.parse(f.resolution_date + "T00:00:00Z") / 1000);
    const res = await send(acct, acct, [callAction("commit", Buffer.from(`${due}|${record}`))]);
    const index = Number(Buffer.from(res.status.SuccessValue, "base64").toString());
    out.commitments.push({ h_months: Number(h), index, tx: res.transaction.hash,
      block_hash: res.transaction_outcome.block_hash, record });
    console.log(`h=${h} committed as index ${index}, tx ${res.transaction.hash}`);
  }
  const dir = path.join(ROOT, "data", "onchain");
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, "commitments.json"), JSON.stringify(out, null, 2) + "\n");
} else if (cmd === "call") {
  const [contract, method, args = ""] = rest;
  const res = await send(acct, contract, [callAction(method, Buffer.from(args))]);
  console.log("tx", res.transaction.hash, Buffer.from(res.status.SuccessValue || "", "base64").toString());
} else if (cmd === "view") {
  console.log(await view(acct, rest[0], rest[1] || ""));
} else {
  console.log("usage: create|deploy|commit|view <account> ...");
}
