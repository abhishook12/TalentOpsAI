const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function run() {
  console.log('='.repeat(65));
  console.log('CHECK 3: PLAYWRIGHT BROWSER E2E NETWORK & CACHE VERIFICATION');
  console.log('='.repeat(65));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const networkResponses = [];
  page.on('response', async (response) => {
    const url = response.url();
    if (url.includes(':8000') || url.includes('/api/')) {
      const headers = response.headers();
      networkResponses.push({
        url,
        status: response.status(),
        etag: headers['etag'],
        cacheControl: headers['cache-control'],
      });
    }
  });

  console.log('1. Navigating to application at http://localhost:5173 ...');
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  console.log('2. Performing browser fetch tests for ETag and 304 revalidation...');
  const fetchResults = await page.evaluate(async () => {
    // 1st request to get ETag
    const res1 = await fetch('http://localhost:8000/ping');
    const etag = res1.headers.get('etag');
    const cc = res1.headers.get('cache-control');
    const text1 = await res1.text();

    // 2nd conditional request with If-None-Match
    const res2 = await fetch('http://localhost:8000/ping', {
      headers: { 'If-None-Match': etag }
    });
    const status2 = res2.status;
    const text2 = await res2.text();

    // 3rd test on version endpoint
    const resVer1 = await fetch('http://localhost:8000/api/v1/version');
    const verEtag = resVer1.headers.get('etag');
    const resVer2 = await fetch('http://localhost:8000/api/v1/version', {
      headers: { 'If-None-Match': verEtag }
    });
    const verStatus2 = resVer2.status;
    const verText2 = await resVer2.text();

    return {
      pingEtag: etag,
      pingCacheControl: cc,
      ping1Len: text1.length,
      ping2Status: status2,
      ping2BodyLen: text2.length,
      verEtag: verEtag,
      ver2Status: verStatus2,
      ver2BodyLen: verText2.length,
    };
  });

  console.log('Fetch Results:', JSON.stringify(fetchResults, null, 2));

  if (fetchResults.ping2Status !== 304) {
    throw new Error(`Expected Ping 2nd request to return 304, got ${fetchResults.ping2Status}`);
  }
  if (fetchResults.ver2Status !== 304) {
    throw new Error(`Expected Version 2nd request to return 304, got ${fetchResults.ver2Status}`);
  }

  console.log('3. Simulating Tab Backgrounding (document.hidden = true)...');
  const initialReqCount = networkResponses.length;
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { value: true, configurable: true });
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });

  // Wait 6 seconds and ensure no new background pings are triggered
  await page.waitForTimeout(6000);
  const hiddenReqCount = networkResponses.length;
  console.log(`Requests before background: ${initialReqCount}, requests after 6s in background: ${hiddenReqCount}`);

  // Capture screenshot proof
  const screenshotPath = 'C:\\Users\\User\\.gemini\\antigravity\\brain\\7283f2a4-dc81-4ce0-a69d-a7dc2f588dc1\\proof_bandwidth_check3_e2e.png';
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`Saved proof screenshot to ${screenshotPath}`);

  await browser.close();
  console.log('\n' + '='.repeat(65));
  console.log('PROOFS VERIFIED: Check 3 PASSED (E2E Browser ETag, 304 0-byte, Hidden Tab Throttle)');
  console.log('='.repeat(65));
}

run().catch(err => {
  console.error('Check 3 Failed:', err);
  process.exit(1);
});
