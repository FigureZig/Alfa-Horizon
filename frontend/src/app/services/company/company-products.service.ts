import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { CreditProductDto } from '@/app/types/company/credit-product-dto'
import { companyProductsMockAdapter } from '@/app/mocks/company-products'

const ROUTE_PREFIX_COMPANIES = 'v1/companies'

export const companyProductsService = {
  async fetchProducts($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<CreditProductDto[]>>(
      `${ROUTE_PREFIX_COMPANIES}/${encodeURIComponent(inn)}/products`,
      {
        params: { lang: locale },
        // Пока нет API, ответ отдаёт мок. Удалите adapter, чтобы запрос ушёл на бэкенд.
        adapter: companyProductsMockAdapter,
      },
    )
  },
}
