import { defineConfig } from '@playwright/test'

// Prueba de extremo a extremo: requiere la API (puerto 8000) y el frontend (puerto 5173) en ejecución.
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: {
    baseURL: process.env.WEB_URL ?? 'http://localhost:5173',
    viewport: { width: 1366, height: 860 },
    launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
  },
})
