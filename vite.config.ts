import path from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  // Tauri expects a fixed port and should fail rather than pick another one.
  server: { port: 1420, strictPort: true },
  // Tauri reads the built assets from disk; relative paths keep it portable.
  base: './',
  build: { target: 'esnext' },
})
