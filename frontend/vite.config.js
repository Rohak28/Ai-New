import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Support PUBLIC_URL passed from terminal or fallback to relative './'
  base: process.env.PUBLIC_URL || './',
  build: {
    // NeuroNest platform standard specifies 'build' directory (npx serve -s build -l 6001)
    outDir: 'build',
  },
  server: {
    port: 6001,
    host: '0.0.0.0',
    allowedHosts: true,
  },
  preview: {
    port: 6001,
    host: '0.0.0.0',
    allowedHosts: true,
  }
})
