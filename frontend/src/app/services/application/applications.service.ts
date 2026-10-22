import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { ApplicationsSummaryDto } from '@/app/types/application/applications-summary-dto'
import { applicationsSummaryMockAdapter } from '@/app/mocks/applications-summary'

const ROUTE_PREFIX_COMPANIES = 'v1/companies'

export const applicationsService = {
  // Предлагаемый маршрут: в текущем API сводки заявок и задач нет
  async fetchSummary($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<ApplicationsSummaryDto>>(
      `${ROUTE_PREFIX_COMPANIES}/${encodeURIComponent(inn)}/applications/summary`,
      {
        params: { lang: locale },
        // Пока нет API, ответ отдаёт мок. Удалите adapter, чтобы запрос ушёл на бэкенд.
        adapter: applicationsSummaryMockAdapter,
      },
    )
  },
}
