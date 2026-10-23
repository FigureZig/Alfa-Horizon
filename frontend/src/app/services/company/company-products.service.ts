import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { Nullable } from '@/app/types/nullable'
import type { ApiResponse } from '@/app/types/api-response'
import type { CompanyOffersDto } from '@/app/types/company/company-offers-dto'
import type { CreditProductDto } from '@/app/types/company/credit-product-dto'

const ROUTE_PREFIX_COMPANIES = 'v1/companies'

// Задача, сумма и срок необязательны: без них подбор общий
export interface CompanyOffersParams {
  goal: Nullable<CreditGoalEnum>
  amount: Nullable<number>
  termMonths: Nullable<number>
}

export const companyProductsService = {
  // Подбор без цели: нужен, когда предодобренного нет, — по нему видно, что мешает
  async fetchOffers($fetch: AxiosInstance, inn: string, locale: AppLocale, params?: CompanyOffersParams) {
    return await $fetch.get<ApiResponse<CompanyOffersDto>>(
      `${ROUTE_PREFIX_COMPANIES}/${encodeURIComponent(inn)}/offers`,
      {
        params: {
          goal: params?.goal ?? undefined,
          amount: params?.amount ?? undefined,
          term_months: params?.termMonths ?? undefined,
          lang: locale,
        },
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
