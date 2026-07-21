/**
 * fp_knife_shot.js — browser proof for the CONSTRAINT-BAKE landmine
 * (spike landmine #4): the knife-throw clip's influence-keyed ChildOf
 * release, exported via export_fp_hands.py, must survive the glTF bake —
 * the knife has to DETACH in three.js, not just in Blender.
 *
 * Numeric probe per sample time: knife node world position + world scale
 * and the right-hand armature node world position -> knife-hand distance.
 * Verdict:
 *   - distance ~constant while in hand (t < release ~0.85 s)
 *   - distance grows fast after release (free flight downrange)
 *   - knife world scale CONSTANT across the switch (the 3.118 swap trap)
 * Plus screenshots (pulled-back cam) for the eye.
 *
 * Usage: node tools/fp_knife_shot.js
 * Expects ~/Kore/fp_hands_test.glb to be the knife export.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium, firefox } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');

const ROOT = '/home/khaled/Kore';
const OUT = process.env.SHOT_OUT || '/tmp/claude-1000/fp_knife_shots';
const TIMES = [0.05, 0.4, 0.75, 0.83, 0.88, 0.95, 1.1, 1.31];

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
    const server = await serve();
    const url = `http://127.0.0.1:${server.address().port}/tools/fp_hands_test.html`;
    let browser;
    try { browser = await chromium.launch(); } catch { browser = await firefox.launch(); }
    const page = await browser.newPage({ viewport: { width: 960, height: 720 }, deviceScaleFactor: 1 });
    page.on('pageerror', (e) => process.stderr.write(`PAGE ERROR: ${e.message}\n`));
    await page.goto(url);
    await page.waitForFunction(() => window.__info && window.__info.status !== 'loading', null, { timeout: 60000 });
    await page.waitForTimeout(500);

    const info = await page.evaluate(() => window.__info);
    console.log(JSON.stringify(info, null, 1));
    if (info.status !== 'ok') { await browser.close(); server.close(); process.exit(2); }

    const save = async (name) => {
        const data = await page.evaluate(() => window.__shot());
        const png = Buffer.from(data.split(',')[1], 'base64');
        fs.writeFileSync(path.join(OUT, name), png);
        console.log('wrote', name, png.length, 'bytes');
    };

    await page.evaluate(() => { window.__paused = true; });

    const probes = [];
    for (const t of TIMES) {
        const p = await page.evaluate((tt) => {
            window.__seek(tt);
            const root = window.__sceneRoot;
            let knife = null, hand = null;
            root.traverse((o) => {
                if (/ThrowingKnife|Knife|Cone/i.test(o.name) && !knife) knife = o;
                if (/^Armature(\.|_)?001$/.test(o.name) && !hand) hand = o;
            });
            if (!hand) root.traverse((o) => { if (/Armature/i.test(o.name) && !hand) hand = o; });
            if (!knife) return { t: tt, error: 'no knife node' };
            const kp = knife.getWorldPosition(new (knife.position.constructor)());
            const ks = knife.getWorldScale(new (knife.position.constructor)());
            const hp = hand ? hand.getWorldPosition(new (hand.position.constructor)()) : null;
            const dist = hp ? kp.distanceTo(hp) : null;
            return {
                t: tt,
                knife: knife.name,
                kpos: kp.toArray().map((v) => +v.toFixed(3)),
                kscale: ks.toArray().map((v) => +v.toFixed(3)),
                hand: hand ? hand.name : null,
                dist: dist === null ? null : +dist.toFixed(3),
            };
        }, t);
        probes.push(p);
        console.log('PROBE', JSON.stringify(p));
    }
    fs.writeFileSync(path.join(OUT, 'probes.json'), JSON.stringify(probes, null, 1));

    // visual frames: default cam + pulled back so the flight stays in view
    for (const t of [0.05, 0.75, 0.88, 1.1]) {
        await page.evaluate((tt) => window.__seek(tt), t);
        await save(`knife_${t.toFixed(2).replace('.', '_')}.png`);
    }
    await page.evaluate(() => window.__lookFrom(0.2, 0.35, -1, 2.4));
    for (const t of [0.83, 0.95, 1.2]) {
        await page.evaluate((tt) => window.__seek(tt), t);
        await save(`knife_wide_${t.toFixed(2).replace('.', '_')}.png`);
    }
    await browser.close();
    server.close();
}

run().catch((e) => { console.error(e); process.exit(1); });
