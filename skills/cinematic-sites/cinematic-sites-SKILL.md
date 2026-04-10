---
name: cinematic-sites
description: >
  Build cinematic, scroll-animated websites from any existing URL. Use this skill whenever the user
  wants to create a premium landing page, cinematic website, scroll-driven site, animated hero website,
  or transform/redesign an existing website into something visually impressive. Also trigger when the
  user mentions "cinematic", "scroll animation", "hero video", "frame sequence", "Kling", "Nano Banana",
  "WaveSpeed", "GSAP ScrollTrigger website", or wants to deploy a static site to Vercel. Covers the
  full pipeline: brand extraction, AI image generation, AI video animation, scroll-driven frame sequence
  build, cinematic module integration, and free Vercel deployment.
---

# Cinematic Sites

Transform any website into a cinematic experience with AI-generated 3D animations, scroll-driven effects, and premium design — then deploy live.

**Four steps. One command. Any business.**

```
/cinematic-sites https://example.com
```

---

## HARD RULES (ENFORCE EVERY BUILD)

These override any defaults. No exceptions.

- **Single HTML file only** — all CSS in `<style>`, all JS in `<script>`. No external CSS/JS files.
- **No placeholder images** — every image must be generated or sourced from the brand. Never use unsplash, picsum, placeholder.com, via.placeholder, placehold.co, or lorem-style URLs.
- **No Lorem Ipsum** — all copy must be real, extracted from the brand or written to match their voice. Write real copy using the brand's tone.
- **Dark theme by default** — unless the brand's existing palette is explicitly light. Dark backgrounds make cinematic video heroes pop.
- **Mobile-first responsive** — every section must work on 375px screens. Use `clamp()` for all font sizes. Test before delivering.
- **Performance budget** — total page weight under 5MB (excluding hero frames). Compress all JPEG frames to quality 75. Lazy-load below-fold images.
- **GSAP + ScrollTrigger only** — no other animation libraries. No Framer Motion, no AOS, no Animate.css, no Lenis.
- **No framework dependencies** — no React, Vue, Svelte, Next.js, Tailwind, or npm. Vanilla HTML/CSS/JS only.
- **No generic fonts** — never use Inter, Roboto, Arial, or system-ui. Pick distinctive heading + body font pairings from Google Fonts that match the brand's personality.
- **No AI-slop aesthetics** — no purple gradients on white, no cookie-cutter card grids, no generic SaaS layouts. Every site must feel designed for its specific brand context.
- **Accessibility baseline** — semantic HTML, `alt` text on images, sufficient color contrast (4.5:1 minimum), keyboard-navigable menus, focus-visible states.
- **Attribution footer** — every build includes a minimal fixed-bottom footer with blurred background and branding attribution.

---

## Prerequisites

### 1. Google Cloud (for image generation)

- Create a project at https://console.cloud.google.com
- Enable the Generative Language API
- Get your API key from API & Services → Credentials
- Set: `GOOGLE_API_KEY=your_key_here`
- New accounts get $300 free credit

### 2. WaveSpeed (for video animation)

- Go to: https://wavespeed.ai → Settings → API Keys
- Set: `WAVESPEED_API_KEY=your_key_here`

### 3. Vercel (for free deployment)

- Install: `npm i -g vercel` → `vercel login`
- Hobby tier is free, unlimited static sites

---

## Step 1: Brand Analysis

Fetch the target website and extract brand identity.

### What to Extract

- Business name and category
- Color palette (primary, secondary, accent, background, text — hex codes)
- Typography (heading and body fonts)
- Key copy (headline, tagline, services, CTA, contact info)
- Logo URL
- Screenshots (if JS-rendered, use Firecrawl with `formats: ["branding"]`)

### How

```bash
curl -sL -o /tmp/site_raw.html "<URL>" -A "Mozilla/5.0"
```

Or use Firecrawl:

```
mcp__firecrawl-mcp__firecrawl_scrape with formats: ["branding"]
```

### Output: Visual Brand Card

Generate `brand-card.html` showing color swatches, font samples, extracted copy, logo preview, suggested theme. Open in browser for review.

The brand card should include:
- **Business name** and tagline
- **Industry tags** (e.g., Japanese Restaurant, Ramen, Bubble Tea)
- **Color palette** with labeled swatches: Background, Card, Accent, Secondary, Text, Muted, Border (all hex codes)
- **Typography** section: Heading font (from original site), Cultural/decorative font if applicable, Body font
- **Key Copy** fields: Headline, Tagline, Suggested Hero Line, Suggested CTA
- **Theme Direction** — a short paragraph describing the visual mood (e.g., "Dark, warm, cinematic. Steam rising from a ramen bowl. Moody lighting. Japanese cultural elements — noren curtains, wooden textures, kanji.")

### Pause Point

Show the brand card. Ask: "Does this look right? Any corrections?"

---

## Step 2: Scene Generation

### 2a. Suggest 3 Concepts

Present a visual table — each with ONE hero object, distinct visual style, clear animation description with motion words.

### Scene Design Rules (from animated-website skill)

- **One subject, one action.** Single hero item, 2-3 supporting elements max.
- **Cinematic, not catalog.** Close-ups, shallow depth of field, dramatic angles. Contextual environments.
- **NO default white backgrounds.** Match environment to industry.
- **Only generate the FIRST FRAME.** Kling animates better from a single image + descriptive prompt.

### 2b. Generate Image (Nano Banana Pro)

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

Save the generated image. Show to user for approval before animating.

### 2c. Animate (Kling via WaveSpeed)

**Model options (ask the user which to use):**

| Model | Endpoint slug | Cost/5s | Notes |
|-------|--------------|---------|-------|
| **Kling O3 Pro** (latest) | `kwaivgi/kling-video-o3-pro/image-to-video` | $0.56 | Best quality, latest model |
| Kling v3.0 Pro | `kwaivgi/kling-v3.0-pro/image-to-video` | $0.56 | Previous gen, proven reliable |
| Kling O3 Standard | `kwaivgi/kling-video-o3-std/image-to-video` | $0.42 | Budget option, still good |
| Kling v3.0 Standard | `kwaivgi/kling-v3.0-std/image-to-video` | $0.42 | Budget previous gen |

**Default: Kling O3 Pro** unless the user specifies otherwise.

### Resolution control (720p vs 1080p):

WaveSpeed has NO resolution parameter — output resolution matches the INPUT IMAGE dimensions. To control output resolution:

- **1080p (default):** Generate or resize the source image to **1920x1080** before uploading
- **720p:** Resize source image to **1280x720** before uploading

Always default to 1080p. Resize with:

```bash
ffmpeg -i input.jpg -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" output_1080p.jpg
```

### Upload image to litterbox (NOT catbox):

```bash
curl -s -F "reqtype=fileupload" -F "time=24h" -F "fileToUpload=@output_1080p.jpg" https://litterbox.catbox.moe/resources/internals/api.php
```

This returns a public URL. Use it as the `image` parameter in the WaveSpeed API call.

### WaveSpeed API call:

```bash
# Submit the task
curl --location --request POST "https://api.wavespeed.ai/api/v3/${ENDPOINT_SLUG}" \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer ${WAVESPEED_API_KEY}" \
  --data-raw '{
    "prompt": "<MOTION_DESCRIPTION>",
    "image": "<LITTERBOX_IMAGE_URL>",
    "negative_prompt": "blur, distort, low quality, shaky camera",
    "cfg_scale": 0.5,
    "duration": 5
  }'
```

The response contains a `requestId`. Poll for the result:

```bash
# Get the result
curl --location --request GET "https://api.wavespeed.ai/api/v3/predictions/${requestId}/result" \
  --header "Authorization: Bearer ${WAVESPEED_API_KEY}"
```

Download the video when status is `completed`. The `outputs[0]` field contains the video URL.

### Extract Frames

Once you have the hero video, extract JPEG frames for the scroll-driven animation:

```bash
mkdir -p frames
ffmpeg -i hero_video.mp4 -vf "fps=24" frames/frame_%04d.jpg
```

Optimize frame file size:
```bash
for f in frames/*.jpg; do
  convert "$f" -quality 75 -resize 1920x1080 "$f"
done
```

---
💡
## Step 3: Website Build

### Design Thinking (before writing code)

Before scaffolding, commit to a clear aesthetic direction. Answer these:

1. **Purpose** — What does this business need visitors to feel? (trust, hunger, luxury, excitement)
2. **Tone** — Pick a specific vibe: moody-cinematic, warm-artisan, bold-modern, refined-luxury, playful-energetic, editorial-clean. Avoid generic "professional".
3. **Hero moment** — What's the ONE thing someone will remember? (the scroll animation, a kinetic text reveal, the accordion menu)
4. **Typography pairing** — Pick a distinctive display font for headings + a refined body font. Never use Inter, Roboto, or system fonts. Match the font to the brand personality:
   - Ramen shop → Oswald (bold industrial) + Outfit (clean modern) + Noto Serif JP (cultural accent)
   - Jewelry → Playfair Display + Outfit
   - Tech/SaaS → Space Mono + Outfit
   - Bakery → DM Serif Display + Outfit
5. **Color dominance** — One dominant color (usually --bg), one sharp accent. Avoid evenly-distributed palettes.

### Architecture Rules

- **One file** — all CSS in `<style>`, all JS in `<script>`
- **Assets external** — video and frames by relative path
- **No build step** — no React, Vue, npm, Tailwind
- **CDN only** — Google Fonts, GSAP + ScrollTrigger, Lucide Icons

### Required CDN

```html
<!-- FONTS: Replace with brand-appropriate fonts. These are defaults only. -->
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<!-- Add cultural/decorative fonts as needed, e.g.: -->
<!-- <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;700&display=swap" rel="stylesheet"> -->

<!-- ANIMATION: Always include both GSAP and ScrollTrigger -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>

<!-- ICONS: Lucide for lightweight, sharp icons -->
<script src="https://unpkg.com/lucide@latest"></script>
```

### Design System Foundation

Every site uses this CSS variable structure. Map brand colors to it:

```css
:root {
  --bg: [from brand];
  --card: [slightly off from bg];
  --text: [high contrast against bg];
  --muted: [for captions only, NOT body text];
  --accent: [brand primary];
  --accent-light: [accent at 8% opacity];
  --border: [subtle divider];
}
```

### Standard Easing

The entire cinematic modules library uses one easing curve for interactive transitions. Use it everywhere:

```css
transition: all 0.4s cubic-bezier(.16, 1, .3, 1);
```

### Site Structure

```
1. HERO — Scroll-driven canvas (300vh, sticky inner, JPEG frame sequence via gsap.to + snap)
2. CINEMATIC MODULES — 2-4 modules from the library woven into content sections
3. SERVICES / FEATURES — Business offerings
4. ABOUT / STORY — Business copy
5. CONTACT / CTA — Phone, email, address
6. FOOTER — Minimal + 123marketing.app attribution bar
```

### Hero Content Layout

Hero text must be a tight vertical stack centered over the canvas. The hero content sits on top of the scroll-driven frame animation using absolute/fixed positioning with z-index layering.

```css
.hero-content {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
  text-align: center;
  pointer-events: none;
}

.hero-content h1 {
  font-size: clamp(2.5rem, 8vw, 6rem);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.05;
  color: var(--text);
  text-shadow: 0 2px 20px rgba(0,0,0,0.5);
}

.hero-content .tagline {
  font-size: clamp(0.875rem, 2vw, 1.25rem);
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-top: 1rem;
}
```

### Scroll-Driven Hero Animation (Frame Sequence)

This is the core cinematic effect. It pins a `<canvas>` element and scrubs through extracted video frames as the user scrolls:

```javascript
// Frame sequence setup
const canvas = document.getElementById('hero-canvas');
const ctx = canvas.getContext('2d');
const frameCount = <TOTAL_FRAMES>;
const images = [];
const currentFrame = { value: 0 };

// Preload frames
for (let i = 0; i < frameCount; i++) {
  const img = new Image();
  img.src = `frames/frame_${String(i + 1).padStart(4, '0')}.jpg`;
  images.push(img);
}

// Render function
function render() {
  const frame = Math.floor(currentFrame.value);
  if (images[frame] && images[frame].complete) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(images[frame], 0, 0, canvas.width, canvas.height);
  }
}

// GSAP ScrollTrigger
gsap.to(currentFrame, {
  value: frameCount - 1,
  snap: "value",
  ease: "none",
  scrollTrigger: {
    trigger: ".hero-section",
    start: "top top",
    end: "bottom bottom",
    pin: ".hero-inner",
    scrub: 0.5,
  },
  onUpdate: render
});

// Set canvas dimensions
images[0].onload = () => {
  canvas.width = images[0].width;
  canvas.height = images[0].height;
  render();
};
```

### Quality Standards

**Typography:**
- Body text minimum 16px (`1rem`), captions minimum 14px
- Use `clamp()` for all heading sizes: `clamp(min, preferred, max)`
- Letter-spacing: tight for headings (`-0.02em`), wider for uppercase labels (`0.1em+`)
- Line height: 1.05-1.1 for display text, 1.5-1.6 for body

**Interactions:**
- All buttons must have hover states using the standard easing curve
- Interactive elements need both `:hover` and `:focus-visible` states
- Buttons should have subtle scale transforms on hover: `transform: scale(1.02)`
- Links should use underline-offset and decoration-thickness for refined styling

**Layout:**
- Navigation: sticky/fixed with `backdrop-filter: blur(20px)` and semi-transparent background
- Sections: clear visual separation through generous spacing (minimum `6rem` between sections), not borders
- Use asymmetric layouts and grid-breaking elements where appropriate
- Images and canvas: `object-fit: cover` for responsive behavior

**Atmosphere:**
- Add depth through layered shadows, not flat borders
- Consider noise/grain textures on backgrounds for analog warmth
- Use `mix-blend-mode` on decorative elements for visual richness
- Smooth scrolling: `html { scroll-behavior: smooth; }`

**Footer:**
- Fixed bottom bar with `backdrop-filter: blur(20px)` and `background: rgba(var(--bg-rgb), 0.8)`
- Attribution text in `--muted` color, small font size
- Include link to 123marketing.app

---

### Cinematic Modules Integration

### Source

The Cinematic Modules library should be cloned into your skills folder during initial setup:

```bash
# Claude Code (VS Code) — run once
cd .claude/skills/
git clone https://github.com/RZhelevPhD/cinematic-site-components.git cinematic-modules

# Antigravity — run once (adjust path to your agent's workspace)
git clone https://github.com/RZhelevPhD/cinematic-site-components.git /path/to/agent/skills/cinematic-modules
```

**Expected local path:** `.claude/skills/cinematic-modules/`

The library contains 30 standalone HTML modules organized into 4 categories. Each module is a single self-contained HTML file with inline CSS + JS. No build step required.

### How to Use Modules

1. **Pick 2-4 modules** that match the brand's industry and vibe (see guide below)
2. **Read the module HTML** from the local skills folder:
   ```bash
   # Local (preferred — no network needed)
   cat .claude/skills/cinematic-modules/accordion-slider.html

   # Fallback: fetch from GitHub if local copy unavailable
   curl -sL https://raw.githubusercontent.com/RZhelevPhD/cinematic-site-components/master/accordion-slider.html
   ```
3. **Extract the CSS and JS** — each module's `<style>` and `<script>` blocks contain everything
4. **Adapt** the styles and scripts into the site, remapping colors to the brand's `--accent`, `--bg`, etc.
5. **Replace placeholder content** — swap demo text/images with the brand's actual content

### Module Filenames (for fetching)

| Module | Filename |
|--------|----------|
| Text Mask Reveal | `text-mask.html` |
| Sticky Stack Narrative | `sticky-stack.html` |
| Layered Zoom Parallax | `zoom-parallax.html` |
| Horizontal Scroll Hijack | `horizontal-scroll.html` |
| Sticky Card Stack | `sticky-cards.html` |
| Scroll SVG Draw | `svg-draw.html` |
| Curtain Reveal | `curtain-reveal.html` |
| Split Screen Scroll | `split-scroll.html` |
| Scroll Color Shift | `color-shift.html` |
| Cursor-Reactive | `cursor-reactive.html` |
| Accordion Slider | `accordion-slider.html` |
| Cursor Image Reveal | `cursor-reveal.html` |
| Hover Image Trail | `image-trail.html` |
| 3D Flip Cards | `flip-cards.html` |
| Magnetic Repel Grid | `magnetic-grid.html` |
| Spotlight Border Cards | `spotlight-border.html` |
| Drag-to-Pan Grid | `drag-pan.html` |
| View Transition Morphing | `view-transitions.html` |
| Particle Explosion Button | `particle-button.html` |
| Odometer Counter | `odometer.html` |
| 3D Coverflow Carousel | `coverflow.html` |
| Dynamic Island Nav | `dynamic-island.html` |
| macOS Dock Nav | `dock-nav.html` |
| Text Scramble Decode | `text-scramble.html` |
| Kinetic Marquee | `kinetic-marquee.html` |
| Mesh Gradient Background | `mesh-gradient.html` |
| Circular Text Path | `circular-text.html` |
| Glitch Effect | `glitch-effect.html` |
| Typewriter Effect | `typewriter.html` |
| Gradient Stroke Text | `gradient-stroke.html` |

### Module Selection Guide by Industry

| Industry | Recommended Modules |
|----------|-------------------|
| Luxury (jewelry, watches, perfume) | Text Mask Reveal, Curtain Reveal, Spotlight Border Cards, Zoom Parallax |
| Food (pizza, bakery, sushi, chocolate) | Color Shift, Zoom Parallax, Kinetic Marquee, Accordion Slider |
| Tech / SaaS | Sticky Stack Narrative, Odometer Counter, Text Scramble, Glitch Effect |
| Fitness / Sport | Split Screen Scroll, Particle Button, Kinetic Marquee, Horizontal Scroll |
| Real Estate / Interiors | Sticky Card Stack, Drag-to-Pan Grid, Curtain Reveal, Zoom Parallax |
| Fashion / Beauty | Image Trail, Flip Cards, Text Mask Reveal, Accordion Slider |
| Restaurants / Bars | Accordion Slider, Color Shift, SVG Draw, Typewriter Effect |
| Creative Agency | Horizontal Scroll, Magnetic Grid, Glitch Effect, Coverflow Carousel |
| Children's Services | Flip Cards, Particle Button, Kinetic Marquee, Mesh Gradient |
| Education / Consulting | Sticky Stack Narrative, Odometer Counter, Typewriter Effect, View Transitions |

### The 30 Modules Reference

**Scroll-Driven (9):**
01 Text Mask Reveal, 02 Sticky Stack Narrative, 03 Layered Zoom Parallax, 04 Horizontal Scroll Hijack, 05 Sticky Card Stack, 06 Scroll SVG Draw, 07 Curtain Reveal, 08 Split Screen Scroll, 09 Scroll Color Shift

**Cursor & Hover (8):**
10 Cursor-Reactive, 11 Accordion Slider, 12 Cursor Image Reveal, 13 Hover Image Trail, 14 3D Flip Cards, 15 Magnetic Repel Grid, 16 Spotlight Border Cards, 17 Drag-to-Pan Grid

**Click & Tap (6):**
18 View Transition Morphing, 19 Particle Explosion Button, 20 Odometer Counter, 21 3D Coverflow Carousel, 22 Dynamic Island Nav, 23 macOS Dock Nav

**Ambient & Auto (7):**
24 Text Scramble Decode, 25 Kinetic Marquee, 26 Mesh Gradient Background, 27 Circular Text Path, 28 Glitch Effect, 29 Typewriter Effect, 30 Gradient Stroke Text

---

## Step 4: Deploy to Vercel

### Prepare the project

```bash
# Create deployment directory
mkdir -p deploy
cp index.html deploy/
cp -r frames/ deploy/frames/

# If you have any other assets (logo, images), copy them too
cp *.jpg *.png deploy/ 2>/dev/null || true
```

### Deploy

```bash
cd deploy

# First time: link to Vercel (creates .vercel/ directory)
vercel link --yes

# Deploy to production
vercel deploy --prod --yes
```

If the project does not exist yet on Vercel, `vercel link` will create it. The `--yes` flag skips interactive prompts and uses defaults.

The deploy command returns the live URL as stdout. Capture it:

```bash
LIVE_URL=$(vercel deploy --prod --yes)
echo "Site is live: $LIVE_URL"
```

### Post-deployment

```bash
# Verify the deployment
vercel curl / --deployment $LIVE_URL

# Check for errors
vercel logs --environment production --level error --since 5m

# Add custom domain (optional)
vercel domains add clientdomain.com
vercel domains inspect clientdomain.com
```

After adding a domain, Vercel automatically provisions an SSL certificate. The client updates their DNS A record to point to Vercel's IP (shown in CLI output).

### Iterate

If the client requests changes:
1. Edit `index.html` locally
2. Re-run `vercel deploy --prod` from the deploy directory
3. The same URL updates automatically

### Pause Point

Share the deployed URL. Ask: "Site is live! Take a look and let me know if you want any changes."

---

## Workflow Summary

```
INPUT: Website URL
  │
  ├─ Step 1: Brand Analysis
  │   └─ Extract colors, fonts, copy → brand-card.html → USER APPROVAL
  │
  ├─ Step 2: Scene Generation
  │   ├─ 2a: Suggest 3 hero concepts → USER PICKS
  │   ├─ 2b: Generate image (Nano Banana Pro) → USER APPROVAL
  │   ├─ 2c: Animate image (Kling via WaveSpeed) → USER PICKS best video
  │   └─ Extract frames from video
  │
  ├─ Step 3: Website Build
  │   ├─ Scaffold HTML with brand design system
  │   ├─ Integrate scroll-driven hero (frame sequence)
  │   ├─ Add 2-4 cinematic modules
  │   ├─ Build content sections from brand copy
  │   └─ USER REVIEW in browser
  │
  └─ Step 4: Deploy to Vercel
      └─ Push live → share URL → USER FEEDBACK

OUTPUT: Live cinematic website
```
