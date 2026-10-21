import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import App from '@/app/App.vue'
import { FinoPreset } from '@/theme/preset'
import '@/style.css'
import '@/theme/palette.css'
import 'primeicons/primeicons.css'
import { router } from '@/app/router'
import { i18n } from '@/app/i18n'
import ToastService from 'primevue/toastservice'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(ToastService)

app.use(PrimeVue, {
    theme: {
        preset: FinoPreset,
        options: {
            darkModeSelector: '.app-dark',
            cssLayer: {
                name: 'primevue',
                order: 'theme, base, primevue, utilities',
            },
        },
    },
})

app.mount('#app')
