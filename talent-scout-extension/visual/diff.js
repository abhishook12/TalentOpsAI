// ============================================================
// visual/diff.js — Perceptual Regional Change Detector & Noise Suppressor
// Algorithms 5, 9, 29: Region-Weighted Diffing, Noise & Spinner Suppression
// ============================================================

window.TalentScout = window.TalentScout || {};
window.TalentScout.Visual = window.TalentScout.Visual || {};

(function() {
  'use strict';

  const DEFAULT_CHANGE_THRESHOLD = 0.035; // 3.5% meaningful regional change threshold
  const DOWNSCALE_WIDTH = 64;
  const DOWNSCALE_HEIGHT = 64;

  let canvas = null;
  let ctx = null;
  let prevFrameData = null;

  function getCanvas() {
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.width = DOWNSCALE_WIDTH;
      canvas.height = DOWNSCALE_HEIGHT;
      ctx = canvas.getContext('2d', { willReadFrequently: true });
    }
    return { canvas, ctx };
  }

  /**
   * Convert image source to downscaled grayscale Uint8Array
   */
  async function getImagePixels(imageSource) {
    const { ctx } = getCanvas();
    ctx.clearRect(0, 0, DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT);

    let img = imageSource;
    if (typeof imageSource === 'string') {
      img = await new Promise((resolve, reject) => {
        const i = new Image();
        i.onload = () => resolve(i);
        i.onerror = reject;
        i.src = imageSource;
      });
    }

    ctx.drawImage(img, 0, 0, DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT);
    const imgData = ctx.getImageData(0, 0, DOWNSCALE_WIDTH, DOWNSCALE_HEIGHT);
    const pixels = imgData.data;

    // Convert to grayscale buffer (64x64 = 4096 bytes)
    const gray = new Uint8Array(DOWNSCALE_WIDTH * DOWNSCALE_HEIGHT);
    for (let i = 0, j = 0; i < pixels.length; i += 4, j++) {
      gray[j] = (pixels[i] * 0.299 + pixels[i + 1] * 0.587 + pixels[i + 2] * 0.114) | 0;
    }
    return gray;
  }

  /**
   * Algorithm 29: Region-Based Change Detection
   * Main Content (middle 70% vertical & horizontal) gets 80% weight.
   * Header/Footer/Margins get 20% weight to suppress noise from clocks, spinners, tabs.
   */
  function computeRegionalDifferenceScore(pixelsA, pixelsB) {
    if (!pixelsA || !pixelsB || pixelsA.length !== pixelsB.length) return 1.0;

    let mainRegionDelta = 0;
    let mainRegionPixels = 0;
    let outerRegionDelta = 0;
    let outerRegionPixels = 0;

    const PIXEL_TOLERANCE = 16; // ignore sensor noise / micro-compression artifacts

    for (let y = 0; y < DOWNSCALE_HEIGHT; y++) {
      const isMainY = y >= 8 && y <= 56; // middle 75%
      for (let x = 0; x < DOWNSCALE_WIDTH; x++) {
        const isMainX = x >= 6 && x <= 58; // middle 80%
        const idx = y * DOWNSCALE_WIDTH + x;

        const delta = Math.abs(pixelsA[idx] - pixelsB[idx]);
        if (delta > PIXEL_TOLERANCE) {
          if (isMainY && isMainX) {
            mainRegionDelta += delta;
            mainRegionPixels++;
          } else {
            outerRegionDelta += delta;
            outerRegionPixels++;
          }
        }
      }
    }

    const totalMainPixels = 48 * 52; // ~2496 pixels
    const totalOuterPixels = (DOWNSCALE_WIDTH * DOWNSCALE_HEIGHT) - totalMainPixels; // ~1600 pixels

    const mainRatio = mainRegionPixels / totalMainPixels;
    const outerRatio = outerRegionPixels / totalOuterPixels;

    // Weighted score favoring main content changes over header/spinner noise
    const weightedScore = (mainRatio * 0.8) + (outerRatio * 0.2);
    return Number(weightedScore.toFixed(4));
  }

  /**
   * Check against last cached baseline
   */
  async function evaluateFrame(newImageSource, customThreshold) {
    try {
      const currentPixels = await getImagePixels(newImageSource);
      if (!prevFrameData) {
        prevFrameData = currentPixels;
        return { isMeaningful: true, score: 1.0, isBaseline: true };
      }

      const score = computeRegionalDifferenceScore(prevFrameData, currentPixels);
      const threshold = customThreshold || DEFAULT_CHANGE_THRESHOLD;
      const isMeaningful = score >= threshold;

      if (isMeaningful) {
        prevFrameData = currentPixels;
      }

      return {
        isMeaningful,
        score,
        isBaseline: false,
      };
    } catch (e) {
      return { isMeaningful: true, score: 1.0, error: e.message };
    }
  }

  function resetBaseline() {
    prevFrameData = null;
  }

  // Export to window.TalentScout.Visual.Diff
  window.TalentScout.Visual.Diff = {
    getImagePixels,
    computeRegionalDifferenceScore,
    evaluateFrame,
    resetBaseline,
    DEFAULT_CHANGE_THRESHOLD,
  };

})();
