/**
 * fp_hands_shot.js — headless proof screenshots of the GLB export spike
 * (tools/fp_hands_test.html). Serves ~/Kore over HTTP, loads the page in
 * Playwright chromium, scrubs the clip to a few times, captures via
 * canvas.toDataURL (preserveDrawingBuffer — plain screenshot can't see
 * WebGL, gotcha #17), writes frames + the page's __info JSON.
 *
 * Usage: node tools/fp_hands_shot.js   (run with cwd anywhere; uses
 *        crescent's playwright install)
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium, firefox } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');

const ROOT = '/home/khaled/Kore';
const OUT = process.env.SHOT_OUT || '/tmp/claude-1000/fp_hands_shots';
const TIMES = [0.0, 0.35, 0.6, 0.9];

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
    page.on('console', (m) => process.stderr.write(`console: ${m.text().slice(0, 300)}\n`));
    await page.goto(url);
    await page.waitForFunction(() => window.__info && window.__info.status !== 'loading', null, { timeout: 60000 });
    await page.waitForTimeout(500);

    const info = await page.evaluate(() => window.__info);
    fs.writeFileSync(path.join(OUT, 'info.json'), JSON.stringify(info, null, 1));
    console.log(JSON.stringify(info, null, 1));
    if (info.status !== 'ok') { await browser.close(); server.close(); process.exit(2); }

    const save = async (name) => {
        const data = await page.evaluate(() => window.__shot());
        const png = Buffer.from(data.split(',')[1], 'base64');
        fs.writeFileSync(path.join(OUT, name), png);
        console.log('wrote', name, png.length, 'bytes');
    };

    for (const t of TIMES) {
        await page.evaluate((tt) => window.__seek(tt), t);
        await save(`frame_${t.toFixed(2).replace('.', '_')}.png`);
    }
    // second clip: prove multi-clip playback (guard hold, mid-clip)
    console.log(await page.evaluate(() => window.__playClip('sword_guard')));
    await page.evaluate(() => window.__seek(0.8));
    await save('guard_0_80.png');
    console.log(await page.evaluate(() => window.__playClip('sword_light')));

    // close-ups at the ready pose: front (FP-ish), palm side, top-down
    await page.evaluate(() => window.__seek(0.05));
    await page.evaluate(() => window.__lookFrom(0, 0.3, 1, 0.85));
    await save('close_front.png');
    await page.evaluate(() => window.__lookFrom(0, 0.2, -1, 0.9));
    await save('close_back.png');
    await page.evaluate(() => window.__lookFrom(0, 1, 0.15, 0.9));
    await save('close_top.png');
    await browser.close();
    server.close();
}

run().catch((e) => { console.error(e); process.exit(1); });
