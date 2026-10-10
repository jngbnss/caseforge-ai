import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// 개발 서버의 /api 요청을 백엔드로 넘긴다. 다른 포트를 쓰면 API_TARGET으로 바꾼다.
const apiTarget = process.env.API_TARGET ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': { target: apiTarget, ws: true, rewrite: (path) => path.replace(/^\/api/, '') },
    },
  },
})
