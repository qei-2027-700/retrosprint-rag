import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: { baseURL: 'http://localhost:3000', trace: 'retain-on-failure' },
  webServer: {
    command: 'uv run --directory ../backend python -m http.server 3000 --bind localhost --directory ../frontend/.output/public',
    url: 'http://localhost:3000',
    reuseExistingServer: false,
    timeout: 30000,
  },
})
