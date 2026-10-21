import {
    createRouter,
    createWebHistory,
} from 'vue-router'

import DashboardLayout from '@/app/layouts/DashboardLayout.vue'
import DashboardPage from '@/app/pages/dashboard/DashboardPage.vue'
import ErrorPage from "@/app/pages/error/ErrorPage.vue";
import SandboxPage from '@/app/pages/sandbox/SandboxPage.vue'
import SandboxPersonaBuilderPage from '@/app/pages/sandbox/SandboxPersonaBuilderPage.vue'

export const router = createRouter({
    history: createWebHistory(),

    routes: [
        {
            path: '/',
            component: DashboardLayout,
            children: [
                {
                    path: '',
                    name: 'dashboard',
                    component: DashboardPage,
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
