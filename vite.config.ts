import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Tauri expects a fixed port and should fail rather than pick another one.
  server: { port: 1420, strictPort: true },
  // Tauri reads the built assets from disk; relative paths keep it portable.
  base: './',
  build: { target: 'esnext' },
})
