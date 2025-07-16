// file: frontend/nuxt.config.ts
export default defineNuxtConfig({
  devtools: { enabled: true },
  ssr: false, // This is important for a client-side heavy app on a Pi
  modules: [
    '@pinia/nuxt', // For state management
  ],
  // We will use a CDN for Bootstrap to keep it simple
  app: {
    head: {
      link: [
        { rel: 'stylesheet', href: 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' },
        { rel: 'stylesheet', href: 'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css' }
      ],
      script: [
        { src: 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js', tagPosition: 'bodyClose' }
      ]
    }
  }
})