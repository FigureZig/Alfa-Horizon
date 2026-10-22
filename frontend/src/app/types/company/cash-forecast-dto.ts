import type { CashForecastStatusEnum } from '@/app/types/company/cash-forecast-status-enum'
import type { Nullable } from '@/app/types/nullable'

export interface CashForecastPointDto {
  date: string
  balance: number
}

export interface CashGapDto {
  date: string
  amount: number
}

export interface CashForecastOperationDto {
  id: string
  date: string
  title: string
  amount: number
}

/**
 * K1 — прогноз остатка: точки по дням, самый глубокий разрыв и операции, которые к нему привели.
 */
export interface CashForecastDto {
  status: CashForecastStatusEnum
  horizon_days: number
  currency: string
  points: CashForecastPointDto[]
  cash_gap: Nullable<CashGapDto>
  operations: CashForecastOperationDto[]
}
