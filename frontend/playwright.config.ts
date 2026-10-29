import { defineConfig } from '@playwright/test'
const frontendPort = process.env.RETROSPRINT_E2E_FRONTEND_PORT || '3000'
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: { baseURL: `http://localhost:${frontendPort}`, trace: 'retain-on-failure' },
  webServer: {
    command: `uv run --directory ../backend python -m http.server ${frontendPort} --bind localhost --directory ../frontend/.output/public`,
    url: `http://localhost:${frontendPort}`,
    reuseExistingServer: false,
    timeout: 30000,
  },
})
