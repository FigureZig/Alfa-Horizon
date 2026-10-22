import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { DashboardSummaryCardDto } from '@/app/types/dashboard/dashboard-summary-card-dto'
import { dashboardSummaryMockAdapter } from '@/app/mocks/dashboard'

const ROUTE_PREFIX_DEMO_PERSONAS = 'v1/demo-personas'

export const dashboardService = {
  async fetchSummary($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<DashboardSummaryCardDto[]>>(
      `${ROUTE_PREFIX_DEMO_PERSONAS}/${encodeURIComponent(inn)}/dashboard/summary`,
      {
        params: { lang: locale },
        // Пока нет API, ответ отдаёт мок. Удалите adapter, чтобы запрос ушёл на бэкенд.
        adapter: dashboardSummaryMockAdapter,
      },
    )
  },
}
