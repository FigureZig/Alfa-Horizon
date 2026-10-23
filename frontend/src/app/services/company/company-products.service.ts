import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { CompanyOffersDto } from '@/app/types/company/company-offers-dto'
import type { CreditProductDto } from '@/app/types/company/credit-product-dto'

const ROUTE_PREFIX_COMPANIES = 'v1/companies'

export const companyProductsService = {
  // Подбор без цели: нужен, когда предодобренного нет, — по нему видно, что мешает
  async fetchOffers($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<CompanyOffersDto>>(
      `${ROUTE_PREFIX_COMPANIES}/${encodeURIComponent(inn)}/offers`,
      {
        params: { lang: locale },
      },
    )
  },

  async fetchProducts($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<CreditProductDto[]>>(
      `${ROUTE_PREFIX_COMPANIES}/${encodeURIComponent(inn)}/products`,
      {
        params: { lang: locale },
      },
    )
  },
}
