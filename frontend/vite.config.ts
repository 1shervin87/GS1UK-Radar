import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Two build modes:
//  - default: served by the FastAPI backend (outDir backend/static, talks to /api)
//  - VITE_DATA_MODE=static: fully static site (GitHub Pages) reading JSON from /data
const isStatic = process.env.VITE_DATA_MODE === 'static'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: process.env.VITE_BASE ?? '/',
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
  build: {
    outDir: isStatic ? 'dist' : '../backend/static',
    emptyOutDir: true,
  },
})
