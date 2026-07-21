/**
 * fp_final_shot.js — browser ground-truth proof for assets/fp_hands.glb
 * (the FINAL 11-clip handoff package).
 *
 * Verifies in three.js (the engine's runtime, not Blender's opinion):
 *   1. gltf.animations enumerates EXACTLY the 11 contract clip names,
 *      with durations — printed as ENUM.
 *   2. knife_throw_blade_first: numeric node probe — knife-hand distance
 *      constant in hand, ramping after release; knife world-scale magnitude
 *      constant (~1.001 m, the 4.9*3.118*ROOT_SCALE product) across the
 *      switch. The meters-root integration check.
 *   3. Screenshots mid-action for sword_light, cast_water_strike,
 *      knife_throw_blade_first (+ idle/heavy extras) via the toDataURL path.
 *   4. Node-name dump for the hand joints / armature nodes (for the brief).
 *
 * Usage: node tools/fp_final_shot.js
 * Shots -> $SHOT_OUT (default scratchpad dir printed at start).
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium, firefox } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');

const ROOT = '/home/khaled/Kore';
const OUT = process.env.SHOT_OUT || '/tmp/claude-1000/fp_final_shots';
const EXPECTED = [
    'idle_sword', 'idle_knife',
    'sword_light', 'sword_heavy_lr', 'sword_heavy_rl',
    'knife_throw_blade_first', 'knife_throw_handle_first',
    'cast_air_strike', 'cast_water_strike', 'cast_fire_strike', 'cast_earth_strike',
];
// release = retimed f52 -> 52/60 = 0.8667 s; 0.86 lands INSIDE the one-frame
// scale sign-flip (the documented chiral-bake footnote) and is excluded from
// the constant-scale verdict.
const RELEASE_T = 52 / 60;
const KNIFE_TIMES = [0.05, 0.4, 0.75, 0.83, 0.86, 0.95, 1.15, 1.31, 1.45];

const MIME = { '.html': 'text/html', '.js': 'application/javascript', '.glb': 'model/gltf-binary', '.json': 'application/json' };

function serve() {
    return new Promise((resolve) => {
        const server = http.createServer((req, res) => {
            const urlPath = decodeURIComponent(req.url.split('?')[0]);
            const filePath = path.join(ROOT, urlPath);
            if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) { res.writeHead(404); res.end('nf'); return; }
            res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath)] || 'application/octet-stream' });
            fs.createReadStream(filePath).pipe(res);
        });
        server.listen(0, '127.0.0.1', () => resolve(server));
    });
}

async function run() {
    fs.mkdirSync(OUT, { recursive: true });
    console.log('shots ->', OUT);
    const server = await serve();
    const url = `http://127.0.0.1:${server.address().port}/tools/fp_hands_test.html?glb=/assets/fp_hands.glb`;
    let browser;
    try { browser = await chromium.launch(); } catch { browser = await firefox.launch(); }
    const page = await browser.newPage({ viewport: { width: 960, height: 720 }, deviceScaleFactor: 1 });
    page.on('pageerror', (e) => process.stderr.write(`PAGE ERROR: ${e.message}\n`));
    await page.goto(url);
    await page.waitForFunction(() => window.__info && window.__info.status !== 'loading', null, { timeout: 120000 });
    await page.waitForTimeout(500);

    const info = await page.evaluate(() => window.__info);
    if (info.status !== 'ok') { console.error(JSON.stringify(info)); await browser.close(); server.close(); process.exit(2); }

    // ── 1. clip enumeration (ground truth) ──
    console.log('ENUM', JSON.stringify(info.animations, null, 1));
    console.log('MESHES', JSON.stringify(info.meshes));
    console.log('BBOX_M', JSON.stringify(info.bboxSize));
    const names = info.animations.map(a => a.name).sort();
    const want = [...EXPECTED].sort();
    const match = JSON.stringify(names) === JSON.stringify(want);
    console.log('CLIP_SET', match ? 'EXACT MATCH (11/11)' : 'MISMATCH');
    if (!match) {
        console.log(' missing:', want.filter(n => !names.includes(n)));
        console.log(' extra:  ', names.filter(n => !want.includes(n)));
    }

    // ── 4. node names for the brief (hand joints, armatures, knife, root) ──
    const nodes = await page.evaluate(() => {
        const out = [];
        window.__sceneRoot.traverse(o => {
            if (/hand|forearm|Armature|Knife|Root/i.test(o.name)) out.push(o.type + ':' + o.name);
        });
        return out;
    });
    console.log('NODES', JSON.stringify(nodes));

    await page.evaluate(() => { window.__paused = true; });
    const save = async (name) => {
        const data = await page.evaluate(() => window.__shot());
        fs.writeFileSync(path.join(OUT, name), Buffer.from(data.split(',')[1], 'base64'));
        console.log('wrote', name);
    };
    const play = (n) => page.evaluate((nn) => window.__playClip(nn), n);
    const seek = (t) => page.evaluate((tt) => window.__seek(tt), t);

    // ── 2. knife release numeric probe ──
    await play('knife_throw_blade_first');
    const probes = [];
    for (const t of KNIFE_TIMES) {
        const p = await page.evaluate((tt) => {
            window.__seek(tt);
            const root = window.__sceneRoot;
            let knife = null, hand = null;
            root.traverse((o) => {
                if (/ThrowingKnife/i.test(o.name) && !knife) knife = o;
                if (/^Armature(\.|_)?001$/.test(o.name) && !hand) hand = o;
            });
            if (!knife) return { t: tt, error: 'no knife node' };
            const V = knife.position.constructor;
            const kp = knife.getWorldPosition(new V());
            const ks = knife.getWorldScale(new V());
            const hp = hand ? hand.getWorldPosition(new V()) : null;
            return {
                t: tt,
                kscaleMag: +((Math.abs(ks.x) + Math.abs(ks.y) + Math.abs(ks.z)) / 3).toFixed(4),
                kscale: ks.toArray().map(v => +v.toFixed(4)),
                dist: hp ? +kp.distanceTo(hp).toFixed(4) : null,
            };
        }, t);
        probes.push(p);
        console.log('KNIFE_PROBE', JSON.stringify(p));
    }
    fs.writeFileSync(path.join(OUT, 'knife_probes.json'), JSON.stringify(probes, null, 1));
    const mags = probes.filter(p => Math.abs(p.t - (RELEASE_T - 1 / 120)) > 1 / 90)
        .map(p => p.kscaleMag);
    const scaleOk = Math.max(...mags) - Math.min(...mags) < 0.01;
    const preDist = probes.filter(p => p.t < RELEASE_T - 0.02).map(p => p.dist);
    const inHandOk = Math.max(...preDist) - Math.min(...preDist) < 0.02;
    const flightOk = probes[probes.length - 1].dist > 1.5 * Math.max(...preDist) + 1.0;
    console.log('KNIFE_VERDICT scale_const=%s in_hand_const=%s flight_ramp=%s',
        scaleOk, inHandOk, flightOk);

    // ── 3. screenshots mid-action ──
    const shots = [
        ['idle_sword', 0.5, 'idle_sword_mid'],
        ['sword_light', 0.12, 'sword_light_gather'],
        ['sword_light', 0.46, 'sword_light_strike'],
        ['sword_heavy_lr', 0.55, 'sword_heavy_lr_sweep'],
        ['cast_water_strike', 1.2, 'cast_water_clasp'],
        ['cast_water_strike', 1.86, 'cast_water_fling'],
        ['knife_throw_blade_first', 0.5, 'knife_draw'],
        ['knife_throw_blade_first', 0.88, 'knife_release'],
    ];
    for (const [clip, t, name] of shots) {
        await play(clip);
        await seek(t);
        await save(name + '.png');
    }
    // knife flight, pulled-back cam so the downrange travel is visible
    await play('knife_throw_blade_first');
    await page.evaluate(() => window.__lookFrom(0.2, 0.35, -1, 2.6));
    await seek(1.15);
    await save('knife_flight_wide.png');
    await browser.close();
    server.close();
}

run().catch((e) => { console.error(e); process.exit(1); });
