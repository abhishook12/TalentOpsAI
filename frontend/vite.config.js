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
  }
})
