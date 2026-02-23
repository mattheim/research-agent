#!/usr/bin/env node

const { chromium } = require('playwright');

const USER_AGENT =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36';

const CAPTCHA_HINT =
  'Google results container did not appear within 10 seconds. You may be blocked by CAPTCHA or anti-bot traffic checks.';

function normalizeGoogleRedirect(rawUrl) {
  try {
    const url = new URL(rawUrl, 'https://www.google.com');
    const host = url.hostname.toLowerCase();

    if (!['http:', 'https:'].includes(url.protocol)) return null;

    // Google often wraps outbound links in /url?q=...; unwrap those.
    if ((host === 'google.com' || host.endsWith('.google.com')) && url.pathname === '/url') {
      const q = url.searchParams.get('q');
      if (q && /^https?:\/\//i.test(q)) return q;
      return null;
    }

    if (host === 'google.com' || host.endsWith('.google.com') || host.includes('googleusercontent.com')) {
      return null;
    }

    return url.toString();
  } catch {
    return null;
  }
}

async function tryDismissConsent(page) {
  const keywords = [
    'accept',
    'accept all',
    'i agree',
    'agree',
    'consent',
    'allow all',
    "yes, i'm in",
  ];

  const maybeClickInFrame = async (frame) => {
    try {
      return await frame.evaluate((terms) => {
        const nodes = Array.from(
          document.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]')
        );

        for (const node of nodes) {
          const text = ((node.innerText || node.textContent || node.value || '') + '').trim().toLowerCase();
          if (!text) continue;
          if (terms.some((t) => text.includes(t))) {
            node.click();
            return true;
          }
        }
        return false;
      }, keywords);
    } catch {
      return false;
    }
  };

  // Best-effort only; no throw if not present.
  for (const frame of page.frames()) {
    const clicked = await maybeClickInFrame(frame);
    if (clicked) {
      await page.waitForTimeout(500);
      break;
    }
  }
}

async function googleTopResults(query, opts = {}) {
  if (!query || typeof query !== 'string' || !query.trim()) {
    throw new Error('query is required');
  }

  const headless = opts.headless !== false;
  const params = new URLSearchParams({
    q: query,
    hl: 'en',
    gl: 'us',
    pws: '0',
    num: '5',
  });
  const searchUrl = `https://www.google.com/search?${params.toString()}`;

  let browser;
  try {
    browser = await chromium.launch({ headless });
    const context = await browser.newContext({
      userAgent: USER_AGENT,
      locale: 'en-US',
    });
    const page = await context.newPage();

    await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30_000 });
    await tryDismissConsent(page);

    // If this selector never appears, Google likely served a challenge page.
    await page.waitForSelector('div#search', { timeout: 10_000 });

    let rows = await page.$$eval('div#search .g', (blocks) => {
      const out = [];
      for (const block of blocks) {
        const h3 = block.querySelector('h3');
        if (!h3) continue;
        const anchor = h3.closest('a') || block.querySelector('a[href]');
        if (!anchor) continue;

        const title = (h3.textContent || '').trim();
        const url = (anchor.getAttribute('href') || '').trim();
        if (!title || !url) continue;

        out.push({ title, url });
      }
      return out;
    });

    if (!rows.length) {
      rows = await page.$$eval('div#search h3', (nodes) => {
        const out = [];
        for (const h3 of nodes) {
          const anchor = h3.closest('a');
          if (!anchor) continue;
          const title = (h3.textContent || '').trim();
          const url = (anchor.getAttribute('href') || '').trim();
          if (!title || !url) continue;
          out.push({ title, url });
        }
        return out;
      });
    }

    const deduped = [];
    const seen = new Set();

    for (const row of rows) {
      const normalizedUrl = normalizeGoogleRedirect(row.url);
      if (!normalizedUrl) continue;
      if (!/^https?:\/\//i.test(normalizedUrl)) continue;
      if (seen.has(normalizedUrl)) continue;
      seen.add(normalizedUrl);

      deduped.push({ title: row.title, url: normalizedUrl });
      if (deduped.length >= 5) break;
    }

    return deduped;
  } catch (err) {
    if (String((err && err.message) || '').includes('waitForSelector')) {
      throw new Error(CAPTCHA_HINT);
    }
    throw err;
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

async function main() {
  const args = process.argv.slice(2);
  const headed = args.includes('--headed');
  const queryParts = args.filter((arg) => arg !== '--headed');
  const query = queryParts.join(' ').trim();

  if (!query) {
    console.error('Usage: node google_top_results.js [--headed] "some query"');
    process.exit(1);
  }

  try {
    const results = await googleTopResults(query, { headless: !headed });
    process.stdout.write(`${JSON.stringify(results, null, 2)}\n`);
  } catch (err) {
    console.error(`Error: ${err && err.message ? err.message : String(err)}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { googleTopResults };
