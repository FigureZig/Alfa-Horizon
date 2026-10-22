import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const ROOT_DIR = new URL('.', import.meta.url).pathname
const DEFAULT_API_PROXY_TARGET = 'http://localhost:8000'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ROOT_DIR, '')

  // /api → бэкенд: в разработке фронт ходит в API тем же путём, что и за nginx стенда, без CORS
  const apiProxy = {
    '/api': {
      target: env.API_PROXY_TARGET || DEFAULT_API_PROXY_TARGET,
      changeOrigin: true,
    },
  }

  return {
    plugins: [vue(), tailwindcss()],
    // FEATURE_* — флаги функций, доступны в коде как import.meta.env.FEATURE_*
    envPrefix: ['VITE_', 'FEATURE_'],
    resolve: {
      alias: {
        '@': new URL('./src', import.meta.url).pathname,
      },
    },
    server: { proxy: apiProxy },
    preview: { proxy: apiProxy },
  }
})
