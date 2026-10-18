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
      title: '接続テスト | Retrosprint',
      meta: [{ name: 'description', content: 'Retrosprint の開発用API疎通確認' }],
    },
  },
  typescript: { strict: true, tsConfig: { compilerOptions: { noUncheckedIndexedAccess: true } } },
})
