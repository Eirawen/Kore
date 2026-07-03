# VFX Frame Capture — Agent Usage

## The Problem

Playwright MCP screenshots of WebGL canvases come back black. The GPU draw
buffer is cleared before Chromium composites the screenshot. This happens in
both headless and headed mode.

## The Fix

Two changes make it work:

1. **`preserveDrawingBuffer: true`** on the `THREE.WebGLRenderer` — this tells
   WebGL not to clear the draw buffer after presenting. Without it,
   `toDataURL()` returns a transparent/black image.

2. **`canvas.toDataURL()` via `browser_evaluate`** instead of
   `browser_take_screenshot` — reads directly from the GPU buffer rather than
   relying on Chromium's compositor.

## Files

- `vfx_test_capture.html` — Drop-in replacement for `vfx_test.html` with
  `preserveDrawingBuffer: true` and the capture API on `window.__vfx`.
  Copy or symlink into the browser client's `tools/` directory.

- `capture_vfx.js` — Standalone Node.js script using Playwright directly.
  Run: `node capture_vfx.js [spell] [frames] [outputDir]`

## Using from Playwright MCP Tools

### Step 1: Navigate

```
browser_navigate → http://localhost:8080/tools/vfx_test_capture.html
```

### Step 2: Wait for ready

```
browser_evaluate → "await new Promise(r => { const check = () => window.__vfx?.captureOneFrame ? r(true) : setTimeout(check, 100); check(); })"
```

### Step 3: Fire and capture

```
browser_evaluate → `(async () => {
    const result = await window.__vfx.fireAndCapture('burst', 12, 2);
    return { count: result.count, duration: result.duration };
})()`
```

### Step 4: Get individual frames as data URLs

```
browser_evaluate → `(async () => {
    const result = await window.__vfx.fireAndCapture('burst', 8, 3);
    return result.frames[0];  // First frame as data:image/png;base64,...
})()`
```

### Step 5: Get a contact sheet

```
browser_evaluate → `(async () => {
    const result = await window.__vfx.fireAndCapture('impact', 12, 2);
    const sheet = await window.__vfx.buildContactSheet(result.frames, 4, 480);
    return sheet;  // Single data URL with 4-column grid
})()`
```

### Step 6: Save frames to disk

The data URLs returned can be decoded from base64 and written to files:

```javascript
// In a Node.js context or via Bash:
const base64 = dataURL.replace(/^data:image\/\w+;base64,/, '');
require('fs').writeFileSync('frame.png', Buffer.from(base64, 'base64'));
```

Or from bash:
```bash
echo "$DATA_URL" | sed 's/^data:image\/png;base64,//' | base64 -d > frame.png
```

## Available Spells

| Key     | Spell            | Description                    |
|---------|------------------|--------------------------------|
| burst   | water_burst      | Quick radial burst             |
| charge  | water_charge     | Inward-converging particles    |
| orb     | water_orb        | Dense glowing core             |
| impact  | water_impact_*   | Ring + spray                   |
| full    | Full sequence    | Charge → fly → impact          |

Or pass any registered emitter name directly (e.g. `huge_test`).

## API Reference

All on `window.__vfx`:

- `captureOneFrame(format?, quality?)` — Synchronous, returns one data URL
- `captureFrames(count, {interval, format, quality})` — Async, returns array of {dataURL, timestamp, frameNumber}
- `fireAndCapture(spell, frames, interval)` — Async, fires spell then captures. Returns {frames: string[], duration, spell, count}
- `buildContactSheet(dataURLs, cols, thumbWidth)` — Async, returns single data URL grid image
- `downloadFrame(dataURL, filename)` — Triggers browser download (manual use)
