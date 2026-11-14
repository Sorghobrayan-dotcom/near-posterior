// NEAR client for the forecast registry, Node standard library only (no npm package).
// Signs and sends transactions with node:crypto (ed25519) and the public JSON-RPC.
//
//   node onchain/near.mjs create <account>         new testnet account, key in ~/.near-credentials
//   node onchain/near.mjs deploy <account> <wasm>  deploy the registry contract
//   node onchain/near.mjs commit <account>         commit the registered forecasts
//   node onchain/near.mjs commit-extra <account>   commit the scoreboard and the milestones
//   node onchain/near.mjs lock <account>           keep only a key that can call `resolve`
//   node onchain/near.mjs selftest <account> <stranger> <wasm>  behaviour test on a spare account
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
const pubKey = (pub) => Buffer.concat([u8(0), pub]);
// AddKey with a function-call permission: no allowance limit, one receiver, the listed methods.
const addCallKeyAction = (pub, receiver, methods) => Buffer.concat([u8(5), pubKey(pub), u64(0), u8(0), u8(0),
  str(receiver), u32(methods.length), ...methods.map(str)]);
const deleteKeyAction = (pub) => Buffer.concat([u8(6), pubKey(pub)]);
const callAction = (m, args, gas = 30_000_000_000_000n) => Buffer.concat([u8(2), str(m), bytes(args), u64(gas), u128(0)]);

async function view(acct, method, args = "") {
  const r = await rpc("query", { request_type: "call_function", finality: "final", account_id: acct,
    method_name: method, args_base64: Buffer.from(args).toString("base64") });
  return Buffer.from(r.result).toString("utf8");
}

const csvLine = (l) => { const o = []; let c = "", q = false;
  for (const ch of l) { if (ch === '"') q = !q; else if (ch === "," && !q) { o.push(c); c = ""; } else c += ch; }
  o.push(c); return o; };
const COMMITS = path.join(ROOT, "data", "onchain", "commitments.json");
const REPO = "https://github.com/Sorghobrayan-dotcom/near-posterior";
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
  if (fs.existsSync(COMMITS)) {
    const com = JSON.parse(fs.readFileSync(COMMITS, "utf8"));
    if (com.contract === acct && com.network === NET) {
      com.code_sha256 = crypto.createHash("sha256").update(fs.readFileSync(rest[0])).digest("hex");
      fs.writeFileSync(COMMITS, JSON.stringify(com, null, 2) + "\n");
    }
  }
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
} else if (cmd === "commit-extra") {
  const com = JSON.parse(fs.readFileSync(COMMITS, "utf8"));
  const reg = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "registered_forecast.json"), "utf8"));
  const ms = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "milestones.json"), "utf8"));
  const commit = execSync("git rev-parse HEAD", { cwd: ROOT }).toString().trim();
  const date = reg.forecasts["24"].resolution_date;
  const due = Math.floor(Date.parse(date + "T00:00:00Z") / 1000);
  const fwd = fs.readFileSync(path.join(ROOT, "results", "forward_claims.csv"), "utf8").trim().split(/\r?\n/).slice(1)
    .map(csvLine).filter((r) => r[6] === "24").map((r) => ({ thesis: r[0], k: Number(r[3]), P: Number(r[7]) }));
  const base = { project: "near-posterior", repo: REPO, git_commit: commit, h_months: 24, resolution_date: date };
  const records = {
    scoreboard: { ...base, type: "scoreboard",
      note: "fee growth multiple k stated by each public NEAR thesis, and P = share of comparable protocols that reached it in 24 months",
      rows: fwd, sha256: { "results/forward_claims.csv": sha("results/forward_claims.csv") } },
    milestones: { ...base, type: "milestones", t0: ms.t0, C0: ms.C0,
      note: "coverage C_90 needed at each date to be on the constant-growth line from C0 to 1; a yardstick, not a forecast",
      milestones: ms.milestones.map((m) => ({ date: m.date, C_needed: m.C_needed })) },
  };
  com.extras = com.extras || [];
  for (const [kind, rec] of Object.entries(records)) {
    const record = JSON.stringify(rec);
    const res = await send(acct, acct, [callAction("commit", Buffer.from(`${due}|${record}`))]);
    const index = Number(Buffer.from(res.status.SuccessValue, "base64").toString());
    com.extras.push({ kind, index, tx: res.transaction.hash, record });
    console.log(`${kind} committed as index ${index}, tx ${res.transaction.hash}`);
  }
  fs.writeFileSync(COMMITS, JSON.stringify(com, null, 2) + "\n");
} else if (cmd === "lock") {
  // One transaction: add a key that can only call `resolve` on this account, delete the full-access key.
  const old = loadKey(acct);
  const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");
  const pub = publicKey.export({ format: "der", type: "spki" }).subarray(-32);
  const seed = privateKey.export({ format: "der", type: "pkcs8" }).subarray(-32);
  const pk = "ed25519:" + b58enc(pub);
  const next = credFile(acct).replace(/\.json$/, ".resolve-key.json");
  fs.writeFileSync(next, JSON.stringify({ account_id: acct, public_key: pk,
    private_key: "ed25519:" + b58enc(Buffer.concat([seed, pub])) }), { mode: 0o600 });
  const res = await send(acct, acct, [addCallKeyAction(pub, acct, ["resolve"]), deleteKeyAction(old.pub)]);
  fs.renameSync(credFile(acct), credFile(acct).replace(/\.json$/, ".deleted-full-access-key.json"));
  fs.renameSync(next, credFile(acct));
  console.log("locked, tx", res.transaction.hash, "remaining key", pk, "(function call: resolve)");
  if (fs.existsSync(COMMITS)) {
    const com = JSON.parse(fs.readFileSync(COMMITS, "utf8"));
    if (com.contract === acct && com.network === NET) {
      com.lock = { tx: res.transaction.hash, methods: ["resolve"] };
      fs.writeFileSync(COMMITS, JSON.stringify(com, null, 2) + "\n");
    }
  }
} else if (cmd === "selftest") {
  const [stranger, wasm] = rest;
  let failed = 0;
  const say = (ok, text) => { if (!ok) failed++; console.log((ok ? "PASS " : "FAIL ") + text); };
  const call = (who, method, args) => send(who, acct, [callAction(method, Buffer.from(args))]);
  const val = (res) => Buffer.from(res.status.SuccessValue || "", "base64").toString();
  const refused = async (text, who, method, args, why) => {
    try { await call(who, method, args); say(false, text + " (it was accepted)"); }
    catch (e) { say(String(e.message).includes(why), `${text}: "${why}"`); }
  };
  await send(acct, acct, [deployAction(fs.readFileSync(wasm))]);
  const past = val(await call(acct, "commit", '1|{"t":"past"}'));
  const future = val(await call(acct, "commit", '4102444800|{"t":"future"}'));
  say(Number(future) === Number(past) + 1, `the owner commits two records (indexes ${past} and ${future})`);
  await refused("a stranger cannot commit", stranger, "commit", '1|{"t":"x"}', "only the contract account can write");
  await refused("the owner cannot resolve before the date", acct, "resolve", `${future}|{"outcome":1}`, "resolution date not reached");
  await refused("nobody can attest before the date", stranger, "attest", `${future}|1`, "resolution date not reached");
  await refused("an attestation is 0 or 1", stranger, "attest", `${past}|2`, "outcome must be 0 or 1");
  await call(stranger, "attest", `${past}|0`);
  await refused("one attestation per account", stranger, "attest", `${past}|1`, "already attested");
  await refused("a stranger cannot resolve", stranger, "resolve", `${past}|{"outcome":0}`, "only the contract account can write");
  await call(acct, "resolve", `${past}|{"outcome":1}`);
  await refused("a record resolves once", acct, "resolve", `${past}|{"outcome":0}`, "already resolved");
  const got = JSON.parse(await view(acct, "get", past));
  say(got.record.t === "past" && got.outcome.value.outcome === 1, "get returns the record with the owner's outcome");
  const att = JSON.parse(await view(acct, "attestations", past));
  say(att.length === 1 && att[0].account === stranger && att[0].outcome === 0,
    "attestations returns the stranger's dissenting reading, next to the owner's outcome");
  say(JSON.parse(await view(acct, "get", future)).outcome === null, "the future record has no outcome");
  process.exitCode = failed ? 1 : 0;
} else if (cmd === "call") {
  const [contract, method, args = ""] = rest;
  const res = await send(acct, contract, [callAction(method, Buffer.from(args))]);
  console.log("tx", res.transaction.hash, Buffer.from(res.status.SuccessValue || "", "base64").toString());
} else if (cmd === "view") {
  console.log(await view(acct, rest[0], rest[1] || ""));
} else {
  console.log("usage: create|deploy|commit|view <account> ...");
}
