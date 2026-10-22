import type { CashForecastDto } from '@/app/types/company/cash-forecast-dto'
import type { Nullable } from '@/app/types/nullable'

/**
 * Ответ GET v1/companies/{inn}/insights. `cash_forecast` пустой, если по счёту недостаточно данных.
 */
export interface CompanyInsightsDto {
  inn: string
  cash_forecast: Nullable<CashForecastDto>
}
