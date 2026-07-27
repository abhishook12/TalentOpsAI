import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

import { execSync } from 'child_process';

let commitHash = 'unknown';
try {
  commitHash = execSync('git rev-parse --short HEAD').toString().trim();
} catch (e) {
  // Fallback for Vercel if needed, Vercel sets VERCEL_GIT_COMMIT_SHA
  if (process.env.VERCEL_GIT_COMMIT_SHA) {
    commitHash = process.env.VERCEL_GIT_COMMIT_SHA.substring(0, 7);
  }
}

export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(commitHash)
  },
  server: {
    host: '127.0.0.1',
    allowedHosts: true
  },
  build: {
    target: 'es2022',
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router') || id.includes('@tanstack/react-router')) return 'react-vendor'
            if (id.includes('recharts') || id.includes('d3-')) return 'charts-vendor'
            if (id.includes('@tiptap') || id.includes('prosemirror') || id.includes('tiptap')) return 'editor-vendor'
            if (id.includes('framer-motion')) return 'animation-vendor'
            if (id.includes('xlsx')) return 'xlsx-vendor'
            if (id.includes('axios') || id.includes('@tanstack/react-query')) return 'data-vendor'
            return 'vendor'
          }
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
})
