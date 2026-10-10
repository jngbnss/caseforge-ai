// 백엔드(uvicorn)와 프론트(vite)를 함께 띄운다.  사용: npm run dev:all
// 백엔드 포트는 BACKEND_PORT(기본 8000), 프론트 포트는 FRONTEND_PORT(기본 5173).
import { spawn } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const backendPort = process.env.BACKEND_PORT ?? '8000'
const frontendPort = process.env.FRONTEND_PORT ?? '5173'
const shell = process.platform === 'win32'

const procs = [
  spawn('uv', ['run', 'uvicorn', 'app.main:app', '--port', backendPort, '--reload'], {
    cwd: resolve(root, 'backend'),
    stdio: 'inherit',
    shell,
  }),
  spawn('npx', ['vite', '--port', frontendPort, '--strictPort'], {
    cwd: resolve(root, 'frontend'),
    stdio: 'inherit',
    shell,
    env: { ...process.env, API_TARGET: `http://127.0.0.1:${backendPort}` },
  }),
]

const stop = () => procs.forEach((p) => p.kill())
process.on('SIGINT', stop)
process.on('SIGTERM', stop)
procs.forEach((p) => p.on('exit', (code) => { if (code) stop() }))
console.log(`\n  CaseForge AI → http://localhost:${frontendPort}  (백엔드 :${backendPort})\n`)
