# Video Overlay

A macOS desktop app that composites images, video clips, and countdown timers over your webcam feed in real time — and outputs the result as a virtual camera so Zoom, Teams, and Google Meet see it as a regular camera.

![Electron app showing webcam feed with timer overlay and config panel](assets/screenshot-placeholder.png)

## Features

- **Live canvas compositor** — webcam feed with image/video overlays drawn on top at 25 fps
- **Countdown timer** — configurable MM:SS timer displayed in the top-right of the feed
- **Siren alert** — on timer expiry: rotating red beacon, flashing vignette, and "TIME'S UP!" banner
- **MJPEG stream** — composited output served at `http://localhost:7654` for OBS Browser Source
- **Virtual camera output** — via OBS Virtual Camera, appears as a system camera in any app

---

## Requirements

- macOS 12 or later
- Node.js 18+
- [OBS Studio](https://obsproject.com) (free) — acts as the virtual camera relay

---

## Quick start

```bash
npm install
npm start
```

The app opens and starts an MJPEG stream at `http://localhost:7654`. The banner at the top of the app shows the URL (click it to copy).

---

## OBS setup (one-time)

OBS provides the virtual camera that Zoom/Teams/Meet see. Set it up once:

1. [Download and install OBS](https://obsproject.com)
2. Open OBS → click **+** under Sources → **Browser Source**
3. Set:
   - URL: `http://localhost:7654`
   - Width: `1280`, Height: `720`
   - Check **"Refresh browser when scene becomes active"**
4. Click **Tools → Start Virtual Camera**
5. In Zoom/Teams/Meet → camera settings → select **OBS Virtual Camera**

Both the overlay app and OBS need to be running during your meeting.

---

## Using the app

### Timer
- Enter a duration in `MM:SS` format (e.g. `05:00`)
- **▶ Start** / **⏸ Pause** / **↺ Reset**
- On expiry: siren animation activates automatically
- Toggle **"Flash siren"** and **"Show timer on feed"** to control what appears in the output

### Overlays
- Click **+ Add image / video** to load a file from disk
- Overlays are drawn over the camera feed in the order added
- Click **✕** on any overlay to remove it

### Camera
- The dropdown lists all available camera devices
- Switching updates the feed immediately

---

## Architecture

```
Webcam (getUserMedia)
        │
  Canvas Compositor   ← Timer / Image / Video / Siren overlays
        │
  canvas.toBlob()     (JPEG encode, ~25 fps)
        │
  Electron IPC        (frame:jpeg)
        │
  Node HTTP Server    (MJPEG multipart stream at localhost:7654)
        │
  OBS Browser Source  → OBS Virtual Camera
        │
  Zoom / Teams / Meet
```

**Three layers:**
- **Renderer** (`src/renderer/`) — HTML + Canvas + JS. All overlay and timer logic lives here.
- **Main process** (`src/main.js`) — Node.js. MJPEG HTTP server, frame relay.
- **OBS** — Virtual camera driver (Camera Extension, ships with OBS).

---

## Project structure

```
video-overlay/
├── src/
│   ├── main.js               # Electron main — MJPEG server, IPC
│   ├── preload.js            # Context bridge
│   └── renderer/
│       ├── index.html
│       ├── index.js          # Entry — camera init, compositor start
│       ├── compositor.js     # rAF loop, canvas draw, JPEG encode
│       ├── overlays.js       # Image/video overlay manager
│       ├── timer.js          # Timer state machine
│       ├── siren.js          # Siren beacon + vignette animation
│       ├── ui.js             # Config panel bindings
│       └── style.css
├── plugin/                   # Legacy CoreMediaIO DAL plugin (macOS ≤ 11 only)
│   ├── src/                  # Objective-C++ source
│   ├── build.sh
│   ├── install.sh
│   └── Info.plist
├── assets/
└── package.json
```

---

## Roadmap: native virtual camera (no OBS)

macOS 13+ supports **Camera Extensions** — a DriverKit-based API that lets an app register a true system camera device without any third-party software. This is how modern virtual camera apps (OBS, Camo, mmhmm) work on Sequoia.

### What's needed

| Requirement | Notes |
|---|---|
| Apple Developer Program | $99/year — developer.apple.com/programs/enroll |
| DriverKit camera entitlement | Request via developer.apple.com → Account → Additional Capabilities → DriverKit. Mention "Camera Extension / virtual camera" as the use case. Approval typically takes 2–5 business days. |
| App ID with System Extension capability | Create at developer.apple.com → Certificates, Identifiers & Profiles |

### Implementation plan

Once the entitlement is approved, the Camera Extension replaces the OBS relay entirely:

1. **`camera-extension/`** — Swift package implementing:
   - `VOCExtensionProvider : CMIOExtensionProvider`
   - `VOCExtensionDevice : CMIOExtensionDevice`
   - `VOCExtensionStream : CMIOExtensionStream`
2. **XPC bridge** — Electron main process opens `NSXPCConnection` to the extension and sends JPEG frames directly
3. **System Settings prompt** — user clicks Allow once; extension is registered permanently
4. **"Video Overlay Camera"** appears in every app's camera picker — no OBS, no stream, nothing extra running

The renderer and compositor are unchanged — only the delivery layer swaps out.

### To contribute

If you have the DriverKit camera entitlement and want to implement the Camera Extension layer, the frame format is JPEG, delivered at ~25 fps via IPC. The entry point would be `src/main.js` → `ipcMain.on('frame:jpeg', ...)`.

---

## Legacy DAL plugin

The `plugin/` directory contains a CoreMediaIO DAL plugin written in Objective-C++. DAL plugins were the virtual camera mechanism for macOS 10.x–11.x. **They no longer load on macOS 12.3+ (including Sequoia)** — `cameracaptured` was rewritten to only support Camera Extensions.

The plugin source is kept for reference.

---

## License

MIT
