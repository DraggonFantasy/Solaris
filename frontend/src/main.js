import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import App from './App.vue'
import router from './router'
import uk from './locales/uk.json'
import en from './locales/en.json'
import './assets/main.css'

window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault()

  const reloadKey = 'solaris-preload-reload-at'
  const lastReload = Number(sessionStorage.getItem(reloadKey) || 0)
  if (Date.now() - lastReload > 30_000) {
    sessionStorage.setItem(reloadKey, String(Date.now()))
    window.location.reload()
  }
})

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || 'uk',
  fallbackLocale: 'en',
  messages: { uk, en }
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(i18n)
app.mount('#app')
