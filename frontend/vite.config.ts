import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo, las peticiones a /api se redirigen al backend (FastAPI en el puerto 8000)
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: { '/api': process.env.API_URL ?? 'http://localhost:8000' },
  },
})
