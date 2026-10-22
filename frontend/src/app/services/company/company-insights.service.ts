import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { CompanyInsightsDto } from '@/app/types/company/company-insights-dto'

const ROUTE_PREFIX_COMPANIES = 'v1/companies'

export const companyInsightsService = {
  async fetchInsights($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<CompanyInsightsDto>>(
      `${ROUTE_PREFIX_COMPANIES}/${encodeURIComponent(inn)}/insights`,
      {
        params: { lang: locale },
      },
    )
  },
}
