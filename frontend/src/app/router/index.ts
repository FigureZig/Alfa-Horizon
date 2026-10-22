import {
    createRouter,
    createWebHistory,
} from 'vue-router'

import DashboardLayout from '@/app/layouts/DashboardLayout.vue'
import DashboardPage from '@/app/pages/dashboard/DashboardPage.vue'
import CreditsPage from '@/app/pages/credits/CreditsPage.vue'
import ApplicationsPage from '@/app/pages/applications/ApplicationsPage.vue'
import ApplicationNewPage from '@/app/pages/applications/ApplicationNewPage.vue'
import ApplicationPage from '@/app/pages/applications/ApplicationPage.vue'
import BankDossierPage from '@/app/pages/bank/BankDossierPage.vue'
import BankMetricsPage from '@/app/pages/bank/BankMetricsPage.vue'
import BankQueuePage from '@/app/pages/bank/BankQueuePage.vue'
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
                    props: true,
                },
                {
                    // Родитель без компонента: пункт меню «Заявки» активен на всех страницах заявок
                    path: 'applications',
                    children: [
                        {
                            path: '',
                            name: 'applications',
                            component: ApplicationsPage,
                            props: true,
                        },
                        {
                            // Новая заявка; продукт, сумма, срок и цель подставляются из ?product=&amount=&term=&goal=
                            path: 'new',
                            name: 'application-new',
                            component: ApplicationNewPage,
                            props: true,
                        },
                        {
                            path: ':applicationId',
                            name: 'application',
                            component: ApplicationPage,
                            props: true,
                        },
                    ],
                },
                // Рабочее место банка: только для сотрудников (DashboardLayout уводит клиентов и сотрудников
                // с чужих страниц). Досье вложено в очередь, чтобы пункт меню «Очередь» оставался активным.
                {
                    path: 'bank/queue',
                    children: [
                        {
                            path: '',
                            name: 'bank-queue',
                            component: BankQueuePage,
                            props: true,
                        },
                        {
                            path: ':applicationId',
                            name: 'bank-dossier',
                            component: BankDossierPage,
                            props: true,
                        },
                    ],
                },
                {
                    path: 'bank/metrics',
                    name: 'bank-metrics',
                    component: BankMetricsPage,
                    props: true,
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
