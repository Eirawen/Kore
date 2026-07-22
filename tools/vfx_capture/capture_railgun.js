#!/usr/bin/env node
/**
 * RAILGUN deterministic frame capture. Uses railgun_test.html's
 * freeze/step/cap hooks: the sim only advances when we say so, so every
 * frame is EXACT — including the 8ms mid-draw frame no realtime capture
 * could ever hit.
 *
 * Usage: node capture_railgun.js [outputDir] [level]
 */
// Absolute path: node resolves require() from the SCRIPT dir, and this
// script lives in Kore while playwright lives in crescent's node_modules.
const { chromium } = require('/home/khaled/crescent/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUTPUT_DIR = process.argv[2] || path.join(__dirname, 'output', 'railgun');
const LEVEL = parseInt(process.argv[3] || '1', 10);
const PAGE_URL = process.env.VFX_URL || 'http://localhost:8080/tools/railgun_test.html';

async function main() {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    const browser = await chromium.launch({
        headless: true,
        args: [
            '--use-gl=angle',            // Better WebGL in headless
            '--use-angle=swiftshader',   // Software rendering fallback
            '--enable-webgl',
        ],
    });
    const page = await browser.newPage({ viewport: { width: 960, height: 640 } });
    page.on('console', m => { if (m.type() === 'error') console.log('[page]', m.text()); });
    page.on('pageerror', e => console.log('[pageerror]', e.message));

    await page.goto(PAGE_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction('window.__ready === true', { timeout: 30000 });

    await page.evaluate((lvl) => {
        window.__freeze = true;
        if (lvl !== 1) window.__setLevel(lvl);
        window.__aimAt(-1.2, 1.6, -5.5);   // the column
        window.__step(1 / 60);              // settle one frame
    }, LEVEL);

    const shots = [];
    const cap = async (label) => {
        const dataURL = await page.evaluate(() => window.__cap());
        shots.push({ label, dataURL });
        console.log('[cap]', label);
    };
    const stepN = (n, dt) => page.evaluate(
        ({ n, dt }) => { for (let i = 0; i < n; i++) window.__step(dt); }, { n, dt });

    // ── The sequence ──
    await page.evaluate(() => window.__charge());
    await stepN(15, 1 / 60); await cap('charge 0.25s — crackle');
    await stepN(14, 1 / 60); await cap('charge 0.48s — coin hangtime');

    await page.evaluate(() => window.__fire());
    await stepN(1, 1 / 120); await cap('FIRE +8ms — mid-draw');
    await stepN(2, 1 / 120); await cap('draw +25ms');
    await stepN(2, 1 / 120); await cap('lance fresh +42ms');

    await stepN(4, 1 / 60); await cap('afterglow +0.11s');
    await stepN(4, 1 / 60); await cap('afterglow +0.17s');
    await stepN(5, 1 / 60); await cap('afterglow +0.26s');
    await stepN(5, 1 / 60); await cap('afterglow +0.34s');
    await stepN(5, 1 / 60); await cap('afterglow +0.42s — crumble');
    await stepN(5, 1 / 60); await cap('afterglow +0.50s — dashes');
    await stepN(10, 1 / 60); await cap('gone +0.67s — smoke only');

    for (let i = 0; i < shots.length; i++) {
        const b64 = shots[i].dataURL.replace(/^data:image\/\w+;base64,/, '');
        const file = path.join(OUTPUT_DIR, `rail_${String(i + 1).padStart(2, '0')}.png`);
        fs.writeFileSync(file, Buffer.from(b64, 'base64'));
    }
    fs.writeFileSync(path.join(OUTPUT_DIR, 'manifest.json'),
        JSON.stringify({ level: LEVEL, labels: shots.map(s => s.label) }, null, 1));
    console.log(`[done] ${shots.length} frames → ${OUTPUT_DIR}`);
    await browser.close();
}

main().catch(e => { console.error(e); process.exit(1); });
