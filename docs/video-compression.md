# Hero video compression — manual ffmpeg recipe

> Last updated: 2026-04-08
>
> Current state: `hero-video.mp4` (5.4 MB) and `hero-video-2.mp4` (4.3 MB) are
> served as-is from the project root. Combined ≈10 MB. On a 4G connection
> (~5 Mbps real throughput) this is ~16 seconds of download — long enough that
> the first visit feels broken without a poster image.
>
> **Already done (2026-04-08):** added `poster="brand_assets/hero-poster.png"`
> attribute to both `<video>` tags in `index.html`. Browsers now show that
> still frame instantly while the video downloads. So the launch is no
> longer blocked by the videos being big — it just looks slightly less
> dynamic on first paint.
>
> **What this doc covers:** when you're ready to actually shrink the videos,
> here are the exact ffmpeg commands. Should drop both files to ~1.5 MB
> combined (85% reduction) without visible quality loss for a hero loop.

---

## Step 1: Install ffmpeg

ffmpeg is not currently installed on this machine. Install via:

**Option A — Chocolatey (cleanest):**
```powershell
choco install ffmpeg
```

**Option B — Direct download:**
1. Go to [gyan.dev ffmpeg builds](https://www.gyan.dev/ffmpeg/builds/) → grab "ffmpeg-release-essentials.zip"
2. Extract to `C:\ffmpeg\`
3. Add `C:\ffmpeg\bin` to your system PATH (Windows Settings → System → About → Advanced system settings → Environment Variables → Path → Edit → New → paste path → OK)
4. Open a new terminal and verify: `ffmpeg -version` should print version info

**Option C — winget:**
```powershell
winget install Gyan.FFmpeg
```

---

## Step 2: Compress both videos

Open a terminal in the project root and run these two commands. They take ~30 seconds each on a typical laptop.

```bash
# Hero video 1
ffmpeg -i hero-video.mp4 \
  -c:v libx264 \
  -preset slower \
  -crf 28 \
  -vf "scale='min(1920,iw)':-2" \
  -profile:v main \
  -pix_fmt yuv420p \
  -movflags +faststart \
  -an \
  -y \
  hero-video.optimized.mp4

# Hero video 2
ffmpeg -i hero-video-2.mp4 \
  -c:v libx264 \
  -preset slower \
  -crf 28 \
  -vf "scale='min(1920,iw)':-2" \
  -profile:v main \
  -pix_fmt yuv420p \
  -movflags +faststart \
  -an \
  -y \
  hero-video-2.optimized.mp4
```

**What each flag does:**
- `-c:v libx264` — H.264 codec, universal browser support
- `-preset slower` — better compression at the cost of encoding time (one-time cost, ship-time benefit)
- `-crf 28` — quality factor. 23 is "visually lossless", 28 is "small but still good". For a looping background video where the user isn't focusing on detail, 28 is fine. If you see banding or blockiness, drop to 26 and re-encode.
- `-vf "scale='min(1920,iw)':-2"` — cap width at 1920px (downscale only, never upscale), keep aspect ratio. Anything bigger is wasted on the hero section.
- `-profile:v main` — H.264 Main profile, broadest device support including older iPhones
- `-pix_fmt yuv420p` — required for browser playback and Quicktime compatibility
- `-movflags +faststart` — moves the moov atom to the start of the file so the video can begin playing while still downloading (huge perceptual win)
- `-an` — strips audio. Hero is muted anyway. Saves another ~10-20% file size.

---

## Step 3: Verify and replace

```bash
# See the size delta
ls -lh hero-video.mp4 hero-video.optimized.mp4
ls -lh hero-video-2.mp4 hero-video-2.optimized.mp4

# Test in browser
# Open index.html, verify the hero still looks good

# When happy, replace originals (keep .bak as safety)
mv hero-video.mp4 hero-video.original.mp4.bak
mv hero-video.optimized.mp4 hero-video.mp4
mv hero-video-2.mp4 hero-video-2.original.mp4.bak
mv hero-video-2.optimized.mp4 hero-video-2.mp4
```

The HTML in index.html doesn't change — same `src="hero-video.mp4"`. Just the underlying file is smaller.

---

## Optional: Also add a WebM version for ~30% extra savings on Chrome/Firefox

```bash
ffmpeg -i hero-video.mp4 \
  -c:v libvpx-vp9 \
  -crf 35 \
  -b:v 0 \
  -vf "scale='min(1920,iw)':-2" \
  -an \
  -y \
  hero-video.webm

ffmpeg -i hero-video-2.mp4 \
  -c:v libvpx-vp9 \
  -crf 35 \
  -b:v 0 \
  -vf "scale='min(1920,iw)':-2" \
  -an \
  -y \
  hero-video-2.webm
```

Then in `index.html` change the `<source>` tags:

```html
<video class="hero-video" id="heroVideo" autoplay muted loop playsinline preload="auto" poster="brand_assets/hero-poster.png">
  <source src="hero-video.webm" type="video/webm">
  <source src="hero-video.mp4" type="video/mp4">
</video>
```

The browser picks WebM if it supports it (Chrome, Firefox, Edge, modern Safari) and falls back to MP4 otherwise. WebM with VP9 is typically 25-40% smaller than equivalent-quality H.264.

---

## Expected sizes after compression

| Step | hero-video.mp4 | hero-video-2.mp4 | Total |
|---|---|---|---|
| Current | 5.4 MB | 4.3 MB | **9.7 MB** |
| After CRF 28 H.264 + audio strip | ~1.0 MB | ~0.8 MB | **~1.8 MB** |
| After WebM VP9 (CRF 35) | ~0.7 MB | ~0.6 MB | **~1.3 MB** |

That's an **80-86% reduction**. First-paint stays instant (poster), and the actual video download finishes in ~3 seconds on 4G instead of 16.

---

## Why I (Claude) didn't do this for you

I tried to install ffmpeg via the project's bash but the Antigravity sandbox doesn't have package manager access, and the Windows curl can't download large binaries through the corporate cert chain. Even if I could install it, video encoding takes ~30s of CPU per file and would be a poor use of the agent loop. Running it once locally on your machine is faster and gives you the artifacts directly in the project tree where they belong.

Once you've installed ffmpeg, ping me and I'll write the actual file replacements + verification screenshots without having to run the encoder myself.
