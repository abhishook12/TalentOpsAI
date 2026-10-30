/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        black: "#000000",
        white: "#ffffff",
        brand: {
          DEFAULT: "#B8D5A0",
          glow: "#C9E2B3",
          subtle: "rgba(184, 213, 160, 0.15)",
          border: "rgba(184, 213, 160, 0.35)",
          dark: "#1B1F1C"
        },
        "brand-red": {
          DEFAULT: "#E58D87",
          glow: "#FCA5A5",
          subtle: "rgba(229, 141, 135, 0.15)",
          border: "rgba(229, 141, 135, 0.35)",
          dark: "#2A1817"
        },
        "brand-sage": {
          DEFAULT: "#B8D5A0",
          glow: "#C9E2B3",
          subtle: "rgba(184, 213, 160, 0.15)",
          border: "rgba(184, 213, 160, 0.35)",
          dark: "#1B1F1C"
        },
        "brand-violet": {
          DEFAULT: "#C4B5D9",
          glow: "#D8CCE8",
          subtle: "rgba(196, 181, 217, 0.15)",
          border: "rgba(196, 181, 217, 0.35)",
          dark: "#1F1B24"
        },
        grey: {
          900: "#121212",
          800: "#18181b",
          700: "#27272a",
          600: "#3f3f46",
          500: "#52525b",
          400: "#71717a",
          300: "#a1a1aa",
          200: "#d4d4d8",
          100: "#f4f4f5"
        },
        "on-background": "#ffffff",
        "inverse-surface": "#ffffff",
        "primary": "#ffffff",
        "primary-fixed-dim": "#e4e4e7",
        "secondary-container": "#e41937",
        "surface-container-high": "#1c1c1f",
        "on-tertiary-container": "#a1a1aa",
        "tertiary": "#d4d4d8",
        "on-secondary-fixed": "#ffffff",
        "on-tertiary": "#18181b",
        "surface-container-highest": "#27272a",
        "on-tertiary-fixed": "#121212",
        "on-surface": "#ffffff",
        "on-secondary-container": "#ffffff",
        "inverse-on-surface": "#18181b",
        "on-primary-fixed": "#121212",
        "surface-variant": "#1c1c1f",
        "secondary-fixed-dim": "#fe063f",
        "on-error-container": "#ffdad6",
        "secondary": "#e41937",
        "on-primary-container": "#000000",
        "on-tertiary-fixed-variant": "#52525b",
        "surface-tint": "#e41937",
        "tertiary-container": "#121212",
        "on-secondary": "#ffffff",
        "surface-container": "#121212",
        "primary-container": "#ffffff",
        "inverse-primary": "#71717a",
        "outline": "rgba(255, 255, 255, 0.15)",
        "surface-container-low": "#0a0a0a",
        "secondary-fixed": "#fe063f",
        "on-primary": "#000000",
        "error": "#e41937",
        "surface-dim": "#000000",
        "primary-fixed": "#ffffff",
        "tertiary-fixed-dim": "#d4d4d8",
        "error-container": "#331219",
        "on-primary-fixed-variant": "#52525b",
        "background": "#000000",
        "surface-bright": "#27272a",
        "outline-variant": "rgba(255, 255, 255, 0.12)",
        "on-surface-variant": "#a1a1aa",
        "on-secondary-fixed-variant": "#ffffff",
        "on-error": "#ffffff",
        "surface-container-lowest": "#000000",
        "surface": "#000000",
        "tertiary-fixed": "#ffffff"
      },
      "borderRadius": {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px"
      },
      "spacing": {
        "container-margin": "24px",
        "gutter": "16px",
        "xl": "40px",
        "sm": "8px",
        "md": "16px",
        "unit": "4px",
        "xs": "4px",
        "lg": "24px"
      },
      "fontFamily": {
        "sans": ["-apple-system", "BlinkMacSystemFont", "\"SF Pro Display\"", "\"SF Pro Text\"", "\"SF Pro\"", "\"Helvetica Neue\"", "Helvetica", "Arial", "sans-serif"],
        "body-lg": ["-apple-system", "BlinkMacSystemFont", "\"SF Pro Display\"", "\"SF Pro Text\"", "sans-serif"],
        "body-md": ["-apple-system", "BlinkMacSystemFont", "\"SF Pro Text\"", "\"SF Pro Display\"", "sans-serif"],
        "headline-md": ["-apple-system", "BlinkMacSystemFont", "\"SF Pro Display\"", "sans-serif"],
        "headline-lg": ["-apple-system", "BlinkMacSystemFont", "\"SF Pro Display\"", "sans-serif"],
        "display-lg": ["-apple-system", "BlinkMacSystemFont", "\"SF Pro Display\"", "sans-serif"],
        "label-sm": ["JetBrains Mono", "monospace"],
        "label-md": ["JetBrains Mono", "monospace"]
      },
      "fontSize": {
        "body-lg": ["18px", {"lineHeight": "1.6", "fontWeight": "400"}],
        "body-md": ["16px", {"lineHeight": "1.5", "fontWeight": "400"}],
        "headline-md": ["24px", {"lineHeight": "1.3", "fontWeight": "600"}],
        "headline-lg": ["32px", {"lineHeight": "1.2", "letterSpacing": "-0.01em", "fontWeight": "600"}],
        "display-lg": ["48px", {"lineHeight": "1.1", "letterSpacing": "-0.02em", "fontWeight": "700"}],
        "label-sm": ["12px", {"lineHeight": "1.4", "letterSpacing": "0.05em", "fontWeight": "500"}],
        "label-md": ["14px", {"lineHeight": "1.4", "letterSpacing": "0.05em", "fontWeight": "500"}]
      }
    },
  },
  plugins: [],
}
