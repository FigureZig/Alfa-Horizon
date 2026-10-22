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

// Русские формы множественного числа: 1 день | 2 дня | 5 дней
function getRussianPluralIndex(choice: number): number {
    const value = Math.abs(choice) % 100
    const lastDigit = value % 10

    if (value > 10 && value < 20) return 2
    if (lastDigit === 1) return 0
    if (lastDigit >= 2 && lastDigit <= 4) return 1

    return 2
}

export const i18n = createI18n({
    legacy: false,
    pluralRules: {
        ru: getRussianPluralIndex,
    },
    globalInjection: true,
    locale: getInitialLocale(),
    fallbackLocale: 'ru',
    messages: {
        ru,
        en,
    },
})