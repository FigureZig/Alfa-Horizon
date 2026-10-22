import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { CompanyProfileDto } from '@/app/types/company/company-profile-dto'

const ROUTE_PREFIX_COMPANIES = 'v1/companies'

export const companyProfileService = {
  async fetchProfile($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<CompanyProfileDto>>(
      `${ROUTE_PREFIX_COMPANIES}/${encodeURIComponent(inn)}/profile`,
      {
        params: { lang: locale },
      },
    )
  },
}
