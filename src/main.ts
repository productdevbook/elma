import { createApp } from 'vue'
import App from './App.vue'
import { initTransfers } from './stores/transfers'
import './style.css'

// shadcn themes via a `dark` class, but the webview only gives us the media
// query. Mirror it onto <html> and keep following changes.
const media = window.matchMedia('(prefers-color-scheme: dark)')
const apply = (dark: boolean) => document.documentElement.classList.toggle('dark', dark)
apply(media.matches)
media.addEventListener('change', e => apply(e.matches))

// Progress listeners belong to the app, not to whichever tab is open.
initTransfers()

createApp(App).mount('#app')
