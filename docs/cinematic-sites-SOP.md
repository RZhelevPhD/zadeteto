# Cinematic Sites — Standard Operating Procedure (SOP)

**Version:** 1.0
**Based on:** 123marketing.app Cinematic Sites Agent Kit
**Adapted by:** Rusi (123marketing.app)
**Last updated:** April 2026

---

## Purpose

This SOP documents the end-to-end process for transforming any existing website into a premium, cinematic landing page using AI-generated hero animations, scroll-driven effects, and modular interactive components. The output is a single-file HTML website deployed live on Vercel.

---

## Prerequisites & Setup

### Accounts Required

| Service | What For | Cost | Setup |
|---------|----------|------|-------|
| Google Cloud | Image generation (Imagen / Nano Banana Pro) | Free $300 credit per new Gmail account | console.cloud.google.com → Enable Generative Language API → Get API key |
| WaveSpeed.ai | Video animation (Kling models) | Pay-per-use (~$0.42-$0.56 per 5s clip) | wavespeed.ai → Settings → API Keys |
| Vercel | Free website hosting & deployment | Free (Hobby tier) | `npm i -g vercel` → `vercel login` |
| GitHub | Cinematic Modules library | Free | Clone: `github.com/123marketing/cinematic-site-components` |

### Environment Variables

```bash
export GOOGLE_API_KEY="your_google_api_key"
export WAVESPEED_API_KEY="your_wavespeed_api_key"
```

### Tools Required

- **ffmpeg** — for image resizing and video frame extraction
- **ImageMagick** (convert) — for batch image optimization
- **curl** — for API calls
- **Node.js + npm** — for Vercel CLI
- **A modern browser** — for previewing brand cards and final sites

### First-Time Setup (run once per machine)

```bash
# 1. Install Vercel CLI
npm i -g vercel
vercel login

# 2. Clone the Cinematic Modules library into your skills folder

# For Claude Code (VS Code):
cd your-project/.claude/skills/
git clone https://github.com/RZhelevPhD/cinematic-site-components.git cinematic-modules

# For Antigravity:
# Clone into whatever workspace your agent uses
git clone https://github.com/RZhelevPhD/cinematic-site-components.git /path/to/agent/workspace/cinematic-modules

# 3. Place the SKILL.md
# Copy cinematic-sites-SKILL.md to:
#   Claude Code:  .claude/skills/cinematic-sites/SKILL.md
#   Antigravity:  your agent's skills directory

# 4. Set environment variables
export GOOGLE_API_KEY="your_google_api_key"
export WAVESPEED_API_KEY="your_wavespeed_api_key"
```

**Final folder structure (Claude Code):**
```
your-project/
└── .claude/
    └── skills/
        ├── cinematic-sites/
        │   └── SKILL.md          ← the agent instructions
        └── cinematic-modules/
            ├── CLAUDE.md
            ├── README.md
            ├── index.html         ← visual hub (open in browser to browse all 30)
            ├── accordion-slider.html
            ├── typewriter.html
            └── ... (28 more module files)
```

---

## Step 1: Brand Analysis

### 1.1 Receive the Target

Client provides their current website URL (or you identify a prospect).

### 1.2 Fetch the Website

```bash
curl -sL -o /tmp/site_raw.html "https://example.com" -A "Mozilla/5.0"
```

If the site is JS-rendered (SPA/React), use Firecrawl:
```
mcp__firecrawl-mcp__firecrawl_scrape with formats: ["branding"]
```

### 1.3 Extract Brand Elements

From the raw HTML, extract:

| Element | Where to Find It | Example |
|---------|-------------------|---------|
| Business name | `<title>`, `<h1>`, meta tags | "Ichiraku Japanese Noodle Shop" |
| Category/Industry | Content analysis, meta description | Japanese Restaurant, Ramen |
| Primary color | CSS `:root`, buttons, links | #e8793a (orange) |
| Secondary color | Hover states, borders | #c4382a (red) |
| Background color | `body` or `html` background | #0c0a08 (dark) |
| Text color | Body text color | #f5e6d3 (cream) |
| Heading font | CSS `font-family` on h1-h6 | Oswald |
| Body font | CSS `font-family` on body/p | Outfit |
| Headline copy | Main `<h1>` or hero text | "Ichiraku Japanese Noodle Shop" |
| Tagline | Subtitle, meta description | "Ramen * Bubble Tea * Anime" |
| Services | Menu items, feature sections | Tonkotsu ramen, bubble tea |
| Contact info | Footer, contact page | Address, phone, hours |
| Logo URL | `<img>` in header/nav | Direct URL to logo image |

### 1.4 Generate Brand Card

Create `brand-card.html` — a visual staging page showing:

- Business name + tagline at top
- Industry tags as pills/badges
- Color palette as labeled swatches with hex codes (Background, Card, Accent, Secondary, Text, Muted, Border)
- Typography samples (heading font, cultural/decorative font, body font)
- Key Copy: Headline, Tagline, Suggested Hero Line, Suggested CTA
- Theme Direction: a paragraph describing the overall visual mood

### 1.5 Client Approval

Open `brand-card.html` in browser. Ask the client:
> "Does this look right? Any corrections before we proceed?"

Wait for approval before moving to Step 2.

**Common corrections at this stage:**
- Wrong primary color (they may want a different brand color emphasized)
- Missing services or products
- Preferred tagline different from what's on their current site
- Theme direction adjustment (e.g., "more playful, less moody")

---

## Step 2: Scene Generation

### 2.1 Concept Ideation

Present 3 hero animation concepts. Each concept includes:

- **Name** (e.g., "Steam Rising", "The Pour", "The Bar")
- **Hero object** — ONE central subject
- **Visual style** — camera angle, lighting, mood
- **Animation description** — what moves, how, motion words

**Example concepts for a ramen shop:**

| # | Name | Description |
|---|------|------------|
| 1 | Steam Rising | Single bowl of tonkotsu ramen on dark wooden counter. Camera tight, shallow depth of field. Steam curls upward through moody amber light. Chopsticks resting on rim. Background blurred — warm lanterns, noren curtain. |
| 2 | The Pour | Overhead angle. Rich golden broth being poured slowly into a dark ceramic bowl over perfectly arranged noodles. Dramatic splash in slow motion. Dark background, single warm spotlight from above. |
| 3 | The Bar | Wide shot of an empty ramen bar counter at night. Warm pendant lights, wooden stools, steam rising from behind the counter. Japanese signage glowing softly. Cinematic, atmospheric, no people. |

### 2.2 Client Picks + Refinement

Client selects 1-2 concepts. They may request modifications:
- "Make it shrimp-based instead of pork"
- "Add more steam"
- "Change the angle"

### 2.3 Generate the First Frame

Use Google's Imagen / Nano Banana Pro API to generate a still image:

```javascript
const res = await fetch(
  `https://generativelanguage.googleapis.com/v1beta/models/nano-banana-pro:generateContent?key=${GOOGLE_API_KEY}`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { responseModalities: ['TEXT', 'IMAGE'] }
    })
  }
);
```

**Prompting tips for first frames:**
- Describe the scene as a photograph, not a painting
- Include lighting direction and quality (e.g., "warm amber light from above left")
- Specify camera settings (e.g., "shallow depth of field, f/1.8")
- Include material textures (e.g., "dark wooden counter", "ceramic bowl")
- End with: "Photorealistic, cinematic, 4K quality"

Show generated image to client for approval.

### 2.4 Resize for 1080p

```bash
ffmpeg -i generated_image.jpg -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" hero_1080p.jpg
```

### 2.5 Upload Image

Upload to litterbox (temporary public hosting, 24h expiry):

```bash
IMAGE_URL=$(curl -s -F "reqtype=fileupload" -F "time=24h" -F "fileToUpload=@hero_1080p.jpg" https://litterbox.catbox.moe/resources/internals/api.php)
echo $IMAGE_URL
```

### 2.6 Animate with Kling

**Model selection guide:**

| Budget | Model | Endpoint | Cost/5s |
|--------|-------|----------|---------|
| Best quality | Kling O3 Pro | `kwaivgi/kling-video-o3-pro/image-to-video` | $0.56 |
| Proven reliable | Kling v3.0 Pro | `kwaivgi/kling-v3.0-pro/image-to-video` | $0.56 |
| Budget, good quality | Kling O3 Standard | `kwaivgi/kling-video-o3-std/image-to-video` | $0.42 |
| Budget, previous gen | Kling v3.0 Standard | `kwaivgi/kling-v3.0-std/image-to-video` | $0.42 |

**Submit the animation:**

```bash
REQUEST_ID=$(curl -s --location --request POST \
  "https://api.wavespeed.ai/api/v3/kwaivgi/kling-video-o3-pro/image-to-video" \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer ${WAVESPEED_API_KEY}" \
  --data-raw '{
    "prompt": "Steam rises slowly from the bowl, ingredients settle gently, camera zooms in smoothly to reveal rich broth detail",
    "image": "'${IMAGE_URL}'",
    "negative_prompt": "blur, distort, low quality, shaky camera, text, watermark",
    "cfg_scale": 0.5,
    "duration": 5
  }' | jq -r '.id')

echo "Request ID: $REQUEST_ID"
```

**Poll for result:**

```bash
# Wait ~2-3 minutes, then check
RESULT=$(curl -s --location --request GET \
  "https://api.wavespeed.ai/api/v3/predictions/${REQUEST_ID}/result" \
  --header "Authorization: Bearer ${WAVESPEED_API_KEY}")

echo $RESULT | jq '.status'
# When status is "completed":
VIDEO_URL=$(echo $RESULT | jq -r '.outputs[0]')
curl -o hero_video.mp4 "$VIDEO_URL"
```

**Pro tip:** Generate 2-3 videos from the same image with different prompts. More volume = higher chance of a great result. Kling is probabilistic.

### 2.7 Extract Frames

```bash
mkdir -p frames
ffmpeg -i hero_video.mp4 -vf "fps=24" frames/frame_%04d.jpg

# Optimize file sizes
for f in frames/*.jpg; do
  convert "$f" -quality 75 -resize 1920x1080 "$f"
done

echo "Total frames: $(ls frames/ | wc -l)"
```

---

## Step 3: Website Build

### 3.1 Scaffold the HTML

Create `index.html` with this structure:

1. **`<head>`** — Google Fonts, GSAP + ScrollTrigger CDN, Lucide Icons, `<style>` block
2. **Hero section** — `<canvas>` for frame sequence, overlaid text (hero line + CTA)
3. **Cinematic modules** — 2-4 modules adapted from the library
4. **Content sections** — Services, About/Story, Contact
5. **Footer** — Minimal with attribution
6. **`<script>`** — Frame sequence logic, GSAP animations, module scripts

### 3.2 Design System

Map brand colors to CSS variables:

```css
:root {
  --bg: #0c0a08;        /* from brand card */
  --card: #141210;       /* slightly off from bg */
  --text: #f5e6d3;       /* high contrast */
  --muted: #8a7a6a;      /* captions only */
  --accent: #e8793a;     /* brand primary */
  --accent-light: rgba(232, 121, 58, 0.08);
  --border: #2a2420;     /* subtle divider */
}
```

Standard easing for all transitions:
```css
transition: all 0.4s cubic-bezier(.16, 1, .3, 1);
```

### 3.3 Select Cinematic Modules

Pick 2-4 modules based on industry (see Module Selection Guide in SKILL.md). Read the module code from your local skills folder:

```bash
# Local path (Claude Code / VS Code)
cat .claude/skills/cinematic-modules/accordion-slider.html

# Fallback: fetch from GitHub
curl -sL https://raw.githubusercontent.com/RZhelevPhD/cinematic-site-components/master/accordion-slider.html
```

Extract the `<style>` and `<script>` blocks from each module. Remap any hardcoded colors to use your CSS variables (`--accent`, `--bg`, etc.). Replace placeholder text with the brand's actual content.

### 3.4 Build the Scroll-Driven Hero

The hero section should be 300vh tall with a sticky inner container pinned to the viewport. The `<canvas>` fills the viewport and scrubs through frames as the user scrolls.

Key implementation points:
- Canvas must resize to fill viewport (`width: 100vw; height: 100vh; object-fit: cover`)
- Preload all frames before enabling scroll interaction
- Use `gsap.to` with `snap: "value"` for smooth frame stepping
- Hero text overlays the canvas using `position: absolute; z-index: 10`

### 3.5 Local Preview

Open `index.html` in browser. Check:
- [ ] Hero animation scrubs smoothly on scroll
- [ ] All text is legible against the background
- [ ] Cinematic modules are interactive and responsive
- [ ] Mobile view works at 375px width
- [ ] Navigation links scroll to correct sections
- [ ] Contact info is correct
- [ ] Footer attribution is present

### 3.6 Client Preview

Open the site for the client. Ask for feedback. Common requests:
- "Add an accordion for the menu" → integrate accordion-slider module
- "Change the hero line" → update the `<h1>` text
- "Different animation section" → swap cinematic modules

---

## Step 4: Deploy to Vercel

### 4.1 Prepare

```bash
mkdir -p deploy
cp index.html deploy/
cp -r frames/ deploy/frames/
cp *.jpg *.png deploy/ 2>/dev/null || true
```

### 4.2 Deploy

```bash
cd deploy

# First time: link to Vercel project (creates .vercel/ directory)
vercel link --yes

# Deploy to production
LIVE_URL=$(vercel deploy --prod --yes)
echo "Site is live: $LIVE_URL"
```

The `--yes` flag skips interactive prompts and uses defaults. If the project doesn't exist on Vercel yet, `vercel link` will create it.

### 4.3 Verify

```bash
# Hit the deployed URL to verify
vercel curl / --deployment $LIVE_URL

# Check for errors in the last 5 minutes
vercel logs --environment production --level error --since 5m
```

### 4.4 Share

Vercel returns a live URL. Share it with the client:
> "Your cinematic website is live at https://project-name.vercel.app — take a look and let me know if you want any changes!"

### 4.4 Iterate

If the client requests changes:
1. Edit `index.html` locally
2. Re-run `vercel --prod` from the deploy directory
3. The same URL updates automatically

### 4.6 Custom Domain (Optional)

```bash
vercel domains add clientdomain.com
vercel domains inspect clientdomain.com
```

After adding a domain, Vercel automatically provisions an SSL certificate. The client updates their DNS A record to point to Vercel's IP (shown in the CLI output).

---

## Pricing Guide (for client-facing work)

### Cost Per Build (Your Costs)

| Item | Cost |
|------|------|
| Image generation (Nano Banana Pro) | ~$0.00 (free Google credit) |
| Video animation (Kling, 2-3 attempts) | ~$1.12-$1.68 |
| Vercel hosting | Free |
| **Total per build** | **~$1.12-$1.68** |

### Suggested Client Pricing

| Tier | Includes | Price Range |
|------|----------|-------------|
| Basic | Brand analysis + 1 hero animation + 3 sections + deploy | $500-$1,500 |
| Standard | Above + 3 cinematic modules + menu/gallery section + 2 revision rounds | $1,500-$3,000 |
| Premium | Above + custom animations + content writing + ongoing hosting support | $3,000-$5,000+ |

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Nano Banana returns error | Check API key, ensure Generative Language API is enabled |
| WaveSpeed video is shaky | Generate 2-3 more, pick the smoothest. Add "steady camera" to negative prompt |
| Frames are too large | Reduce quality: `convert -quality 60` instead of 75 |
| Scroll animation is jerky | Reduce frame count: use `fps=15` instead of 24 |
| Vercel deploy fails | Check you're in the correct directory, ensure `vercel login` was completed |
| Site looks bad on mobile | Check `clamp()` font sizes, test at 375px, verify canvas `object-fit: cover` |

---

## File Structure

```
project-name/
├── index.html              # The complete cinematic website
├── brand-card.html          # Brand analysis staging page
├── frames/                  # Extracted JPEG frames from hero video
│   ├── frame_0001.jpg
│   ├── frame_0002.jpg
│   └── ...
├── hero_video.mp4           # Source hero video (not deployed)
├── hero_1080p.jpg           # Generated hero image (not deployed)
└── deploy/                  # Vercel deployment directory
    ├── index.html
    └── frames/
```

---

## Appendix: Cinematic Modules Quick Reference

### Scroll-Driven (9)
01 Text Mask Reveal — Headline fills with color as you scroll
02 Sticky Stack Narrative — Product pins, features scroll past
03 Layered Zoom Parallax — Depth layers, foreground zooms past
04 Horizontal Scroll Hijack — Vertical scroll → horizontal gallery
05 Sticky Card Stack — Cards pin and stack on each other
06 Scroll SVG Draw — Lines draw themselves on scroll
07 Curtain Reveal — Hero splits open like curtains
08 Split Screen Scroll — Two halves scroll opposite directions
09 Scroll Color Shift — Background changes per section

### Cursor & Hover (8)
10 Cursor-Reactive — Glow, 3D tilt, magnetic buttons, ripples
11 Accordion Slider — Strips expand on hover
12 Cursor Image Reveal — Before/after with wipe, spotlight, split
13 Hover Image Trail — Cursor leaves fading images behind
14 3D Flip Cards — Cards rotate to reveal back
15 Magnetic Repel Grid — Tiles push away from cursor
16 Spotlight Border Cards — Borders illuminate under cursor
17 Drag-to-Pan Grid — Infinite draggable canvas

### Click & Tap (6)
18 View Transition Morphing — Elements shape-shift between states
19 Particle Explosion Button — CTAs burst on click
20 Odometer Counter — Digit wheels roll to target
21 3D Coverflow Carousel — Center focused, edges angled
22 Dynamic Island Nav — Pill morphs for notifications
23 macOS Dock Nav — Icons magnify on hover

### Ambient & Auto (7)
24 Text Scramble Decode — Matrix-style character cycling
25 Kinetic Marquee — Infinite text bands, scroll-reactive
26 Mesh Gradient Background — Animated color blobs
27 Circular Text Path — Text on spinning circle
28 Glitch Effect — RGB channel split
29 Typewriter Effect — Text types itself
30 Gradient Stroke Text — Animated gradient on outlined text

**Source:** `https://github.com/123marketing/cinematic-site-components`
**Your fork:** `https://github.com/RZhelevPhD/cinematic-site-components`

---

## Appendix B: Adapting for Your Stack

### If using Claude.ai (not Claude Code)

You can run this entire pipeline from the Claude.ai chat interface with computer use:

1. **Step 1** — paste the target URL, ask Claude to analyze the brand and generate `brand-card.html`. Download and review.
2. **Step 2** — use the Anthropic API artifact feature to call Google's Imagen API directly from an artifact (see `anthropic_api_in_artifacts` docs). For WaveSpeed, create a simple fetch-based artifact.
3. **Step 3** — ask Claude to generate the full `index.html` as a file. Download it.
4. **Step 4** — deploy manually via Vercel CLI on your local machine.

### If using GoHighLevel (for client delivery)

Since your 123marketing.app projects run on GHL:

1. Build the cinematic site using this pipeline
2. Export the final HTML
3. In GHL, create a new funnel page → Custom Code element
4. Paste the full HTML (including `<style>` and `<script>`) into the Custom Code block
5. Host frames on a CDN (Cloudflare R2, AWS S3, or GHL's own media hosting)
6. Update frame paths in the JS to point to the CDN URLs

**Limitation:** GHL's Custom Code element has size limits. For very large sites, use Vercel for hosting and embed via iframe, or link directly from GHL.

### If using Antigravity / VS Code with Claude Code

This is the setup Jay uses in the video. The SKILL.md goes in:
```
.claude/skills/cinematic-sites/SKILL.md
```

The cinematic modules library goes alongside:
```
.claude/skills/cinematic-sites/scroll-stoppers-library.html
```

Claude Code reads the SKILL.md automatically when you invoke `/cinematic-sites`.

### Alternative Image Generation APIs

If Google Cloud credit is exhausted:

| Provider | Model | Cost | Notes |
|----------|-------|------|-------|
| Google (default) | Nano Banana Pro / Imagen | Free $300 credit | Best value for starters |
| Replicate | FLUX 1.1 Pro | ~$0.04/image | High quality, fast |
| OpenAI | DALL-E 3 | ~$0.04/image | Good quality, easy API |
| Stability AI | SDXL / SD3 | ~$0.02/image | Budget option |

### Alternative Video Animation APIs

If WaveSpeed is unavailable:

| Provider | Model | Endpoint | Notes |
|----------|-------|----------|-------|
| WaveSpeed (default) | Kling O3 Pro | wavespeed.ai/api/v3 | Recommended |
| Kling Direct | Kling API | klingai.com | Official, requires Chinese phone |
| Replicate | Kling / Wan 2.1 | replicate.com | Higher latency |
| Fal.ai | Kling / Minimax | fal.ai | Alternative aggregator |
| Runway | Gen-3 Alpha | runwayml.com | Premium, $0.50+/5s |

---

## Appendix C: Outreach and Selling This Service

### Positioning

This service is a premium website transformation. Position it as:

> "Your current website is a booking form. Your competitors have cinematic experiences. We turn your site into something people actually want to scroll through, in 48 hours, deployed live."

### Cold Outreach Angle (for 123marketing.app)

When prospecting local businesses:

1. **Find businesses with weak websites** — booking-only pages, outdated designs, no mobile optimization
2. **Run the brand analysis (Step 1)** without asking permission — it's public data
3. **Generate the brand card** — this becomes your pitch asset
4. **Send the brand card** with a message: "Направих бърз анализ на бранда ви. Ето какво виждам и какво може да се подобри. Искате ли да видите как би изглеждал сайтът ви с кинематографична анимация?"

### What to Show in the Pitch

- Before/after comparison (their current site vs. the cinematic version)
- The brand card (shows you understand their brand)
- 2-3 example cinematic sites from different industries
- The live Vercel URL (they can click and experience it immediately)

### Pricing Psychology

Your cost is ~$1.50 per build. Your time is ~2-4 hours. Price based on value:

- Restaurant/cafe: $500-$1,000 (they see immediate foot traffic value)
- Professional services (lawyer, dentist): $1,500-$3,000 (higher margins, reputation matters)
- E-commerce/luxury: $3,000-$5,000+ (ROI is directly measurable)
