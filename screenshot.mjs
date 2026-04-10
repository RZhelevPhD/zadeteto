import { execFileSync } from 'child_process';
import { readdirSync, mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = join(__dirname, 'temporary screenshots');
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

const url = process.argv[2] || 'http://localhost:3000';
const label = process.argv[3] || '';
const width = parseInt(process.argv[4]) || 1400;
const height = parseInt(process.argv[5]) || 1200;

if (!existsSync(SCREENSHOT_DIR)) mkdirSync(SCREENSHOT_DIR, { recursive: true });

// Auto-increment screenshot number
const existing = readdirSync(SCREENSHOT_DIR).filter(f => f.startsWith('screenshot-'));
let maxN = 0;
existing.forEach(f => {
  const m = f.match(/^screenshot-(\d+)/);
  if (m) maxN = Math.max(maxN, parseInt(m[1]));
});
const n = maxN + 1;
const filename = label ? `screenshot-${n}-${label}.png` : `screenshot-${n}.png`;
const outPath = join(SCREENSHOT_DIR, filename);

console.log(`Capturing ${url} ...`);

try {
  execFileSync(CHROME, [
    '--headless=new',
    '--disable-gpu',
    `--screenshot=${outPath}`,
    `--window-size=${width},${height}`,
    '--hide-scrollbars',
    '--force-device-scale-factor=1',
    '--virtual-time-budget=10000',
    url
  ], {
    timeout: 25000,
    stdio: 'pipe'
  });
  console.log(`Saved: temporary screenshots/${filename}`);
} catch (e) {
  console.error('Screenshot failed:', e.stderr?.toString() || e.message);
  process.exit(1);
}
