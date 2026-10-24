import {
    createRouter,
    createWebHistory,
} from 'vue-router'

import DashboardLayout from '@/app/layouts/DashboardLayout.vue'

declare module 'vue-router' {
    interface RouteMeta {
        // Ключ i18n заголовка вкладки
        title?: string
        // Раздел кабинета: рабочее место банка или голосование участника; без него — кабинет клиента
        area?: 'bank' | 'votes'
        errorCode?: number
    }
}

export const router = createRouter({
    history: createWebHistory(),

    // Новая страница открывается сверху, «назад» возвращает прежнюю прокрутку, якорь — к своему блоку
    scrollBehavior(to, _from, savedPosition) {
        if (savedPosition) return savedPosition
        if (to.hash) return { el: to.hash, behavior: 'smooth' }

        return { top: 0 }
    },

    // Страницы грузятся по требованию: в первый экран не попадают банк, конструктор компании и графики
    routes: [
        {
            // Пользовательский путь начинается с главной продукта, дальше — выбор пользователя
            path: '/',
            name: 'landing',
            component: () => import('@/app/pages/landing/LandingPage.vue'),
            meta: { title: 'pageTitle.landing' },
        },
        {
            // ИНН компании демо-персоны в адресе: кабинет переживает перезагрузку страницы.
            // Формат как в API: 10 цифр — юрлицо, 12 — ИП; иначе сработает страница 404.
            path: '/cabinet/:inn(\\d{10}|\\d{12})',
            component: DashboardLayout,
            props: true,
            children: [
                {
                    path: '',
                    name: 'dashboard',
                    component: () => import('@/app/pages/dashboard/DashboardPage.vue'),
                    props: true,
                    meta: { title: 'pageTitle.dashboard' },
                },
                {
                    path: 'credits',
                    name: 'credits',
                    component: () => import('@/app/pages/credits/CreditsPage.vue'),
                    props: true,
                    meta: { title: 'pageTitle.credits' },
                },
                {
                    // Родитель без компонента: пункт меню «Заявки» активен на всех страницах заявок
                    path: 'applications',
                    children: [
                        {
                            path: '',
                            name: 'applications',
                            component: () => import('@/app/pages/applications/ApplicationsPage.vue'),
                            props: true,
                            meta: { title: 'pageTitle.applications' },
                        },
                        {
                            // Новая заявка; продукт, сумма, срок и цель подставляются из ?product=&amount=&term=&goal=
                            path: 'new',
                            name: 'application-new',
                            component: () => import('@/app/pages/applications/ApplicationNewPage.vue'),
                            props: true,
                            meta: { title: 'pageTitle.applicationNew' },
                        },
                        {
                            path: ':applicationId',
                            name: 'application',
                            component: () => import('@/app/pages/applications/ApplicationPage.vue'),
                            props: true,
                            meta: { title: 'pageTitle.application' },
                        },
                    ],
                },
                // Рабочее место банка: только для сотрудников (DashboardLayout уводит клиентов и сотрудников
                // с чужих страниц). Досье вложено в очередь, чтобы пункт меню «Очередь» оставался активным.
                {
                    // Участник ООО без доступа к счёту видит только голосование по крупной сделке.
                    // Родитель без компонента: пункт меню «Голосование» активен и на странице конкретного голоса
                    path: 'votes',
                    children: [
                        {
                            path: '',
                            name: 'votes',
                            component: () => import('@/app/pages/votes/VotesPage.vue'),
                            props: true,
                            meta: { title: 'pageTitle.votes', area: 'votes' },
                        },
                        {
                            path: ':applicationId',
                            name: 'vote',
                            component: () => import('@/app/pages/votes/VotePage.vue'),
                            props: true,
                            meta: { title: 'pageTitle.vote', area: 'votes' },
                        },
                    ],
                },
                {
                    path: 'bank/queue',
                    children: [
                        {
                            path: '',
                            name: 'bank-queue',
                            component: () => import('@/app/pages/bank/BankQueuePage.vue'),
                            props: true,
                            meta: { title: 'pageTitle.bankQueue', area: 'bank' },
                        },
                        {
                            path: ':applicationId',
                            name: 'bank-dossier',
                            component: () => import('@/app/pages/bank/BankDossierPage.vue'),
                            props: true,
                            meta: { title: 'pageTitle.bankDossier', area: 'bank' },
                        },
                    ],
                },
                {
                    path: 'bank/applications',
                    name: 'bank-applications',
                    component: () => import('@/app/pages/bank/BankApplicationsPage.vue'),
                    props: true,
                    meta: { title: 'pageTitle.bankApplications', area: 'bank' },
                },
                {
                    path: 'bank/metrics',
                    name: 'bank-metrics',
                    component: () => import('@/app/pages/bank/BankMetricsPage.vue'),
                    props: true,
                    meta: { title: 'pageTitle.bankMetrics', area: 'bank' },
                },
            ],
        },
        {
            path: '/login',
            name: 'login',
            component: () => import('@/app/pages/sandbox/SandboxPage.vue'),
            meta: { title: 'pageTitle.login' },
        },
        {
            // Прежний адрес выбора пользователя
            path: '/sandbox',
            redirect: { name: 'login' },
        },
        {
            path: '/login/company',
            name: 'login-company',
            component: () => import('@/app/pages/sandbox/SandboxPersonaBuilderPage.vue'),
            meta: { title: 'pageTitle.loginCompany' },
        },
        {
            // Правка своей компании: id её создателя
            path: '/login/company/:personaId',
            name: 'login-company-edit',
            component: () => import('@/app/pages/sandbox/SandboxPersonaBuilderPage.vue'),
            props: true,
            meta: { title: 'pageTitle.loginCompany' },
        },
        {
            path: '/sandbox/personas/new',
            redirect: { name: 'login-company' },
        },
        {
            path: '/403',
            name: 'forbidden',
            component: () => import('@/app/pages/error/ErrorPage.vue'),
            meta: { errorCode: 403, title: 'pageTitle.forbidden' },
        },
        {
            path: '/500',
            name: 'server-error',
            component: () => import('@/app/pages/error/ErrorPage.vue'),
            meta: { errorCode: 500, title: 'pageTitle.serverError' },
        },
        {
            path: '/:pathMatch(.*)*',
            name: 'not-found',
            component: () => import('@/app/pages/error/ErrorPage.vue'),
            meta: { errorCode: 404, title: 'pageTitle.notFound' },
        },
    ],
})
