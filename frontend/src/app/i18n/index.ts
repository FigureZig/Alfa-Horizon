import { createI18n } from 'vue-i18n'

import ru from './locales/ru'
import en from './locales/en'

export type AppLocale = 'ru' | 'en'

const STORAGE_KEY = 'fino-locale'

function getInitialLocale(): AppLocale {
    const saved = localStorage.getItem(STORAGE_KEY)

    if (saved === 'ru' || saved === 'en') {
        return saved
    }

    return navigator.language.toLowerCase().startsWith('ru')
        ? 'ru'
        : 'en'
}

export const i18n = createI18n({
    legacy: false,
    globalInjection: true,
    locale: getInitialLocale(),
    fallbackLocale: 'ru',
    messages: {
        ru,
        en,
    },
})