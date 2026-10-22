import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { CreditScoreDto } from '@/app/types/company/credit-score-dto'

const ROUTE_PREFIX_COMPANIES = 'v1/companies'

export const companyScoreService = {
  async fetchScore($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<CreditScoreDto>>(
      `${ROUTE_PREFIX_COMPANIES}/${encodeURIComponent(inn)}/score`,
      {
        params: { lang: locale },
      },
    )
  },
}
