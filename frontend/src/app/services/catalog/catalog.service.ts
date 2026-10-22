import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { CatalogProductsDto } from '@/app/types/catalog/catalog-product-dto'
import type { LoanCalcDto, LoanCalcRequestDto } from '@/app/types/catalog/loan-calc-dto'

const ROUTE_PREFIX_CATALOG = 'v1/catalog'
const ROUTE_CALC_LOAN = 'v1/calc/loan'

export const catalogService = {
  async fetchProducts($fetch: AxiosInstance, locale: AppLocale) {
    return await $fetch.get<ApiResponse<CatalogProductsDto>>(
      `${ROUTE_PREFIX_CATALOG}/products`,
      {
        params: { lang: locale },
      },
    )
  },

  // Калькулятор: платёж, переплата и график; без ставки бэкенд считает её по продукту, отрасли и классу риска
  async calculateLoan($fetch: AxiosInstance, payload: LoanCalcRequestDto) {
    return await $fetch.post<ApiResponse<LoanCalcDto>>(ROUTE_CALC_LOAN, payload)
  },
}
