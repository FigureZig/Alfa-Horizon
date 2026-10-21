import { ref } from 'vue'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'fino-theme'

const theme = ref<Theme>('light')

function applyTheme(value: Theme) {
    theme.value = value

    document.documentElement.classList.toggle(
        'app-dark',
        value === 'dark',
    )
}

export function initTheme() {
    const saved = localStorage.getItem(STORAGE_KEY)

    const preferred: Theme =
        saved === 'light' || saved === 'dark'
            ? saved
            : window.matchMedia('(prefers-color-scheme: dark)').matches
                ? 'dark'
                : 'light'

    applyTheme(preferred)
}

export function useTheme() {
    function setTheme(value: Theme) {
        applyTheme(value)
        localStorage.setItem(STORAGE_KEY, value)
    }

    function toggleTheme() {
        setTheme(theme.value === 'dark' ? 'light' : 'dark')
    }

    return { theme, setTheme, toggleTheme }
}