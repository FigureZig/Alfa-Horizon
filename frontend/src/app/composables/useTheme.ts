import { ref } from 'vue'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'fino-theme'
const THEME_TRANSITION_MS = 650

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

    /**
     * Смена темы с анимацией: снимок старой темы сжимается кругом в точку кнопки — цвета «уходят» в неё.
     * Без View Transitions API или при reduced motion тема меняется мгновенно.
     */
    function toggleTheme(origin?: { x: number, y: number }) {
        const next: Theme = theme.value === 'dark' ? 'light' : 'dark'
        const isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

        if (!origin || !document.startViewTransition || isReducedMotion) {
            setTheme(next)

            return
        }

        // Радиус до самого дальнего угла экрана: круг в начале закрывает всё окно
        const radius = Math.hypot(
            Math.max(origin.x, window.innerWidth - origin.x),
            Math.max(origin.y, window.innerHeight - origin.y),
        )
        const transition = document.startViewTransition(() => setTheme(next))

        transition.ready.then(() => {
            document.documentElement.animate(
                {
                    clipPath: [
                        `circle(${radius}px at ${origin.x}px ${origin.y}px)`,
                        `circle(0px at ${origin.x}px ${origin.y}px)`,
                    ],
                },
                {
                    duration: THEME_TRANSITION_MS,
                    easing: 'cubic-bezier(0.7, 0, 0.2, 1)',
                    pseudoElement: '::view-transition-old(root)',
                },
            )
        }).catch(() => {
            // Переход прерван (например, повторным кликом): тема уже применена
        })
    }

    return { theme, setTheme, toggleTheme }
}