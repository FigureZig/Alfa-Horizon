import type { CashForecastDto } from '@/app/types/company/cash-forecast-dto'
import type { CreditProductDto } from '@/app/types/company/credit-product-dto'
import type { Nullable } from '@/app/types/nullable'

// Сколько стоит закрыть разрыв: сумма, на сколько дней и проценты за них
export interface CashGapCoverDto {
  amount: number
  days: number
  interest: number
}

export interface CashGapOfferDto extends CreditProductDto {
  cover: Nullable<CashGapCoverDto>
}

// K5: действующий госконтракт в ЕИС — повод для кредита на исполнение
export interface CompanyContractDto {
  reg_num: string
  customer: string
  price: number
  advance_percent: Nullable<number>
  end_date: Nullable<string>
}

/**
 * Ответ GET v1/companies/{inn}/insights. `cash_forecast` пустой, если по счёту недостаточно данных;
 * `offer` — продукт, который закрывает найденный разрыв; `contract` — сигнал K5.
 */
export interface CompanyInsightsDto {
  inn: string
  cash_forecast: Nullable<CashForecastDto>
  offer?: Nullable<CashGapOfferDto>
  contract?: Nullable<CompanyContractDto>
}
