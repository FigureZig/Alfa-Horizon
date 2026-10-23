import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { RepaymentDto } from '@/app/types/company/repayment-dto'

const ROUTE_PREFIX_COMPANIES = 'v1/companies'

export interface RepaymentParams {
  amount: number
  termMonths: number
  rate: number
  // Бэкенд отвечает 422 для продуктов без графика платежей — по продукту можно не звать заранее
  product?: string
}

export const companyRepaymentService = {
  async fetchRepayment($fetch: AxiosInstance, inn: string, params: RepaymentParams, locale: AppLocale) {
    return await $fetch.get<ApiResponse<RepaymentDto>>(
      `${ROUTE_PREFIX_COMPANIES}/${encodeURIComponent(inn)}/repayment`,
      {
        params: { amount: params.amount, term_months: params.termMonths, rate: params.rate, product: params.product, lang: locale },
      },
    )
  },
}
