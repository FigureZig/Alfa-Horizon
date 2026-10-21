import type { AxiosInstance } from 'axios'
import type { ApiResponse } from '@/app/types/api-response'
import { DashboardStatisticsDto } from "@/app/types/dashboard/dashboard-statistics-dto.ts";

const ROUTE_PREFIX_DASHBOARD = 'v1/dashboard'

export const dashboardService = {
    async fetchDashboard($fetch: AxiosInstance) {
        return await $fetch.get<ApiResponse<DashboardStatisticsDto>>(
            ROUTE_PREFIX_DASHBOARD,
        )
    },
}
