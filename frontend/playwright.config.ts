import { defineConfig, devices } from '@playwright/test'

// E2E 전용 포트. 개발 서버(8000/5173)나 다른 로컬 앱과 겹치지 않게 높은 번호를 쓴다.
const BACKEND_PORT = process.env.E2E_BACKEND_PORT ?? '18765'
const FRONTEND_PORT = process.env.E2E_FRONTEND_PORT ?? '15299'
// webServer.env는 환경 변수를 통째로 바꾸므로 PATH 등을 함께 넘긴다
const env = Object.fromEntries(
  Object.entries(process.env).filter((e): e is [string, string] => e[1] !== undefined),
)

export default defineConfig({
  testDir: 'e2e',
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 } } }],
  webServer: [
    {
      command: `uv run uvicorn app.main:app --port ${BACKEND_PORT}`,
      cwd: '../backend',
      url: `http://127.0.0.1:${BACKEND_PORT}/health`,
      env: { ...env, DATABASE_URL: 'sqlite:///./e2e.db', LLM_BACKEND: 'mock', EMBEDDING_BACKEND: 'mock' },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npx vite --port ${FRONTEND_PORT} --strictPort`,
      url: `http://localhost:${FRONTEND_PORT}`,
      env: { ...env, API_TARGET: `http://127.0.0.1:${BACKEND_PORT}` },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})
