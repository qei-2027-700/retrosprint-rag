import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2026-10-18',
  future: { compatibilityVersion: 5 },
  ssr: false,
  devtools: { enabled: false },
  css: ['~/assets/css/main.css'],
  vite: { plugins: [tailwindcss()] },
  runtimeConfig: {
    public: { apiBaseUrl: 'http://localhost:8000' },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'ja' },
      title: 'Retrosprint',
      meta: [{ name: 'description', content: '振り返りの質問・回答・出典を確認するローカルデモ' }],
    },
  },
  typescript: { strict: true, tsConfig: { compilerOptions: { noUncheckedIndexedAccess: true } } },
})
