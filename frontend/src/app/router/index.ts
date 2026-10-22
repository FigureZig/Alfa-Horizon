import {
    createRouter,
    createWebHistory,
} from 'vue-router'

import DashboardLayout from '@/app/layouts/DashboardLayout.vue'
import DashboardPage from '@/app/pages/dashboard/DashboardPage.vue'
import CreditsPage from '@/app/pages/credits/CreditsPage.vue'
import ApplicationsPage from '@/app/pages/applications/ApplicationsPage.vue'
import ErrorPage from "@/app/pages/error/ErrorPage.vue";
import SandboxPage from '@/app/pages/sandbox/SandboxPage.vue'
import SandboxPersonaBuilderPage from '@/app/pages/sandbox/SandboxPersonaBuilderPage.vue'

export const router = createRouter({
    history: createWebHistory(),

    routes: [
        {
            // Пользовательский путь начинается с выбора демо-персоны
            path: '/',
            redirect: { name: 'sandbox' },
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
                    component: DashboardPage,
                    props: true,
                },
                {
                    path: 'credits',
                    name: 'credits',
                    component: CreditsPage,
                },
                {
                    path: 'applications',
                    name: 'applications',
                    component: ApplicationsPage,
                },
            ],
        },
        {
            path: '/sandbox',
            name: 'sandbox',
            component: SandboxPage,
        },
        {
            path: '/sandbox/personas/new',
            name: 'sandbox-persona-builder',
            component: SandboxPersonaBuilderPage,
        },
        {
            path: '/403',
            name: 'forbidden',
            component: ErrorPage,
            meta: { errorCode: 403 },
        },
        {
            path: '/500',
            name: 'server-error',
            component: ErrorPage,
            meta: { errorCode: 500 },
        },
        {
            path: '/:pathMatch(.*)*',
            name: 'not-found',
            component: ErrorPage,
            meta: { errorCode: 404 },
        },
    ],
})
