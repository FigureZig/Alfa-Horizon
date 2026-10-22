import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  // FEATURE_* — флаги функций, доступны в коде как import.meta.env.FEATURE_*
  envPrefix: ['VITE_', 'FEATURE_'],
  resolve: {
    alias: {
      '@': new URL('./src', import.meta.url).pathname,
    },
  },
})
