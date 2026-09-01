// ============================================================
// visual/diff.js — Perceptual Visual Change Detector & Noise Suppressor
// Lightweight, ultra-fast canvas-based frame comparison
// ============================================================

window.TalentScout = window.TalentScout || {};
window.TalentScout.Visual = window.TalentScout.Visual || {};

(function() {
  'use strict';

  // Configurable thresholds — ultra-sensitive for automatic continuous capture
  const DEFAULT_CHANGE_THRESHOLD = 0.03; // 0.00 = identical, 0.03+ = captures any visual change
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
   * Convert an image bitmap/element/dataUrl to downscaled grayscale Uint8ClampedArray
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
      // Luminance: 0.299 R + 0.587 G + 0.114 B
      gray[j] = (pixels[i] * 0.299 + pixels[i + 1] * 0.587 + pixels[i + 2] * 0.114) | 0;
    }
    return gray;
  }

  /**
   * Compute normalized difference score between two grayscale pixel buffers (0.00 to 1.00)
   */
  function computeDifferenceScore(pixelsA, pixelsB) {
    if (!pixelsA || !pixelsB || pixelsA.length !== pixelsB.length) return 1.0;

    let diffPixels = 0;
    let totalDelta = 0;
    const len = pixelsA.length;
    const PIXEL_DELTA_TOLERANCE = 18; // ignore tiny sensor noise/compression artifacts

    for (let i = 0; i < len; i++) {
      const delta = Math.abs(pixelsA[i] - pixelsB[i]);
      if (delta > PIXEL_DELTA_TOLERANCE) {
        diffPixels++;
        totalDelta += delta;
      }
    }

    const pixelDiffRatio = diffPixels / len;
    const avgIntensityChange = totalDelta / (len * 255);

    // Combined score favoring structural changes
    return Number((pixelDiffRatio * 0.7 + avgIntensityChange * 0.3).toFixed(4));
  }

  /**
   * Check if change is meaningful or merely transient animation/spinner noise
   */
  function isMeaningfulChange(score, threshold = DEFAULT_CHANGE_THRESHOLD) {
    if (score < threshold) return false;
    return true;
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

      const score = computeDifferenceScore(prevFrameData, currentPixels);
      const isMeaningful = isMeaningfulChange(score, customThreshold || DEFAULT_CHANGE_THRESHOLD);

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

  // Export to window.TalentScout.Visual
  window.TalentScout.Visual.Diff = {
    getImagePixels,
    computeDifferenceScore,
    isMeaningfulChange,
    evaluateFrame,
    resetBaseline,
    DEFAULT_CHANGE_THRESHOLD,
  };

})();
