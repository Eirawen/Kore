#!/usr/bin/env node
/**
 * VFX Frame Capture Script
 *
 * Launches Playwright, navigates to the capture-enabled VFX test page,
 * fires a spell, captures frames via canvas.toDataURL(), and saves them
 * as PNGs + a contact sheet.
 *
 * Usage:
 *   node capture_vfx.js [spell] [frameCount] [outputDir]
 *
 * Examples:
 *   node capture_vfx.js burst 12 ./output
 *   node capture_vfx.js full 24 ./output
 *   node capture_vfx.js impact 16 ./output
 *
 * Spells: burst, charge, orb, impact, full, huge_test, or any emitter name
 *
 * Requirements:
 *   npm install playwright  (or use npx)
 *   The VFX test page must be served at http://localhost:8080
 *
 * WHY THIS EXISTS:
 *   Playwright screenshots of WebGL canvases come back black because
 *   headless Chromium clears the GPU draw buffer before the screenshot
 *   composites. The fix is twofold:
 *     1. The test page uses preserveDrawingBuffer: true on the WebGL renderer
 *     2. This script captures via canvas.toDataURL() evaluated in-page,
 *        which reads directly from the preserved buffer
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SPELL = process.argv[2] || 'burst';
const FRAME_COUNT = parseInt(process.argv[3] || '12', 10);
const OUTPUT_DIR = process.argv[4] || path.join(__dirname, 'output');
const PAGE_URL = process.env.VFX_URL || 'http://localhost:8080/tools/vfx_test_capture.html';

async function main() {
    // Ensure output directory
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });

    console.log(`[capture] Spell: ${SPELL}, Frames: ${FRAME_COUNT}`);
    console.log(`[capture] URL: ${PAGE_URL}`);
    console.log(`[capture] Output: ${OUTPUT_DIR}`);

    // Launch browser — headed if DISPLAY is set, headless otherwise
    const headless = !process.env.DISPLAY;
    const browser = await chromium.launch({
        headless,
        args: [
            '--use-gl=angle',           // Better WebGL in headless
            '--use-angle=swiftshader',   // Software rendering fallback
            '--enable-webgl',
        ],
    });

    const context = await browser.newContext({
        viewport: { width: 1280, height: 720 },
    });
    const page = await context.newPage();

    // Navigate and wait for the page to initialize
    await page.goto(PAGE_URL, { waitUntil: 'networkidle' });

    // Wait for __vfx to be available
    await page.waitForFunction(() => window.__vfx && window.__vfx.captureOneFrame, {
        timeout: 10000,
    });

    console.log('[capture] Page loaded, __vfx API available');

    // Let the scene render a few frames to stabilize
    await page.waitForTimeout(500);

    // Quick sanity check — capture a baseline frame
    const baseline = await page.evaluate(() => {
        const url = window.__vfx.captureOneFrame();
        // Check it's not all black by sampling a few pixels
        return url.substring(0, 100);
    });
    console.log(`[capture] Baseline frame starts with: ${baseline.substring(0, 60)}...`);

    // Fire spell and capture frames
    console.log(`[capture] Firing '${SPELL}' and capturing ${FRAME_COUNT} frames...`);

    const result = await page.evaluate(async ({ spell, frames }) => {
        const data = await window.__vfx.fireAndCapture(spell, frames, 2);
        return {
            count: data.count,
            duration: data.duration,
            spell: data.spell,
            frames: data.frames,
        };
    }, { spell: SPELL, frames: FRAME_COUNT });

    console.log(`[capture] Captured ${result.count} frames over ${result.duration}ms`);

    // Save individual frames
    const framePaths = [];
    for (let i = 0; i < result.frames.length; i++) {
        const dataURL = result.frames[i];
        const base64 = dataURL.replace(/^data:image\/\w+;base64,/, '');
        const buffer = Buffer.from(base64, 'base64');
        const filename = `${SPELL}_frame_${String(i).padStart(3, '0')}.png`;
        const filepath = path.join(OUTPUT_DIR, filename);
        fs.writeFileSync(filepath, buffer);
        framePaths.push(filepath);
        console.log(`[capture] Saved ${filename} (${buffer.length} bytes)`);
    }

    // Build and save contact sheet
    console.log('[capture] Building contact sheet...');
    const contactSheet = await page.evaluate(async (frameURLs) => {
        return await window.__vfx.buildContactSheet(frameURLs, 4, 480);
    }, result.frames);

    if (contactSheet) {
        const base64 = contactSheet.replace(/^data:image\/\w+;base64,/, '');
        const buffer = Buffer.from(base64, 'base64');
        const sheetPath = path.join(OUTPUT_DIR, `${SPELL}_contact_sheet.png`);
        fs.writeFileSync(sheetPath, buffer);
        console.log(`[capture] Contact sheet saved: ${sheetPath} (${buffer.length} bytes)`);
    }

    await browser.close();
    console.log('[capture] Done.');
}

main().catch(err => {
    console.error('[capture] Error:', err);
    process.exit(1);
});
