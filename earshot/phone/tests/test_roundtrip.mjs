// EARSHOT phone-channel: full protocol round trip over REAL BroadcastChannel.
// Simulates the two-tab DONE criterion headlessly: a gateway instance emits a
// withheld_card + an approval_request; a phone instance receives them, mints an
// approval_token bound to the plan hash; the gateway verifies and replies.
// Also covers: SILENT card with nudge, notification gating, unknown-type drop,
// and buzz path selection (resolveBuzzPaths never returns empty).
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const dir = dirname(fileURLToPath(import.meta.url));
const phoneDir = join(dir, '..');
for (const f of ['crypto.js', 'channel.js', 'phone.js']) {
  eval(readFileSync(join(phoneDir, f), 'utf8'));
}
const C = globalThis.EarshotCrypto;
const EarshotChannel = globalThis.EarshotChannel;
const EarshotPhone = globalThis.EarshotPhone;
assert(C && EarshotChannel && EarshotPhone, 'scripts failed to load');
assert(typeof BroadcastChannel === 'function', 'Node BroadcastChannel missing');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const seen = { phone: [], gateway: [] };

// --- gateway side (what mcp-server's approve() will do) ---
const store = new Map();
const gateway = new EarshotChannel({ room: 'testroom', backend: 'broadcast' });
await gateway.start(async (msg) => {
  seen.gateway.push(msg.type);
  if (msg.type === 'approval_token') {
    const res = await C.verifyApprovalToken({
      store, requestId: msg.request_id, decision: msg.decision,
      ts: msg.ts, token: msg.token, nowMs: Date.now()
    });
    assert(res.ok, 'gateway rejected a legitimate token: ' + res.outcome);
    await gateway.send({ type: 'approval_result', trace_id: msg.trace_id,
      ts: Date.now(), request_id: msg.request_id, outcome: res.outcome,
      note: 'Detergent reordered — Blinkit, ₹12.40.' });
  }
});

// --- phone side (EarshotChannel + approval minting, DOM-free core) ---
const phoneCh = new EarshotChannel({ room: 'testroom', backend: 'broadcast' });
await phoneCh.start(async (msg) => {
  seen.phone.push(msg.type);
  if (msg.type === 'approval_request') {
    // phone renders EXACT plan (assert fields present), then approves
    assert(msg.plan.amount_cents === 1240, 'phone did not see exact amount');
    assert(msg.plan_hash.length === 64, 'plan_hash malformed');
    const ts = Date.now();
    const token = await C.makeApprovalToken({
      planHash: msg.plan_hash, requestId: msg.request_id, decision: 'approve', ts });
    await phoneCh.send({ type: 'approval_token', trace_id: msg.trace_id,
      ts, request_id: msg.request_id, decision: 'approve', token });
  }
});

// 1. withheld card arrives at the phone
await gateway.send({ v: 1, type: 'withheld_card', id: 'm1', trace_id: 't1',
  ts: Date.now(), card: { item_id: 'cal1', level: 'EXISTENCE', title: 'One private item',
    detail: 'Prenatal checkup — City Clinic, 4:30 PM', speaker_heard: 'One private item, sent to your phone.',
    winning_rule: 'never mention the clinic in front of Mom', nudge: true } });
await sleep(150);
assert(seen.phone.includes('withheld_card'), 'withheld card never arrived');
console.log('ok  withheld_card gateway -> phone');

// 2. SILENT card + notification card (P0-2, branch 8)
await gateway.send({ v: 1, type: 'withheld_card', id: 'm2', trace_id: 't2', ts: Date.now(),
  card: { level: 'SILENT', detail: 'Bank OTP 482913', nudge: true } });
await gateway.send({ v: 1, type: 'notification_card', id: 'm3', trace_id: 't3', ts: Date.now(),
  card: { source: 'package_tracker', detail: 'Instax Mini 12 delivered', announcement_suppressed: true } });
await sleep(150);
assert(seen.phone.filter((t) => t === 'withheld_card').length >= 2, 'SILENT card lost');
assert(seen.phone.includes('notification_card'), 'notification card lost');
console.log('ok  SILENT + notification cards arrive (P0-2)');

// 3. unknown types are dropped (Postel)
const before = seen.phone.length;
await gateway.send({ v: 1, type: 'future_type_v99', id: 'mx', ts: Date.now() });
await sleep(150);
assert.strictEqual(seen.phone.length, before, 'unknown type was not ignored');
console.log('ok  unknown message type ignored');

// 4. full approval round trip: request -> token -> verify -> result
const plan = { action: 'reorder', merchant: 'Blinkit',
  items: [{ name: 'Detergent 1kg', qty: 1 }], amount_cents: 1240, currency: 'INR' };
const ph = await C.planHash(plan);
store.set('apr_rt', { planHash: ph, expiresAt: Date.now() + 120000, consumed: false });
await gateway.send({ v: 1, type: 'approval_request', id: 'm4', trace_id: 't4',
  ts: Date.now(), request_id: 'apr_rt', expires_at: Date.now() + 120000,
  plan, plan_hash: ph, speaker_heard: 'Reordering detergent — check your phone to confirm.' });
await sleep(300);
assert(seen.gateway.includes('approval_token'), 'approval token never reached gateway');
assert(seen.phone.includes('approval_result'), 'approval result never reached phone');
console.log('ok  EXISTENCE-with-signature round trip: request -> token -> verified -> result');

// 5. buzz path selection: never empty, vibrate only when supported
assert.deepStrictEqual(
  EarshotPhone.resolveBuzzPaths({ vibrate: () => true }), ['vibrate', 'audio', 'visual']);
assert.deepStrictEqual(
  EarshotPhone.resolveBuzzPaths({}), ['audio', 'visual'],
  'desktop (no vibrate) must still fire audio+visual');
assert.deepStrictEqual(
  EarshotPhone.resolveBuzzPaths(undefined), ['audio', 'visual'],
  'missing navigator must still fire audio+visual');
console.log('ok  buzz fallback never silent (vibrate / audio+visual)');

gateway.close(); phoneCh.close();
console.log('\nALL ROUND-TRIP TESTS PASSED');
process.exit(0);
