import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    proxy: {
      '/api/run-stream': 'http://localhost:8000',
      '/api/run-all': 'http://localhost:8000',
      '/api/reset': 'http://localhost:8000',
      '/api/status': 'http://localhost:8000',
    },
  },
})
