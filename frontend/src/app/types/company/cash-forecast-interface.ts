import type { CashForecastStatusEnum } from '@/app/types/company/cash-forecast-status-enum'
import type { Nullable } from '@/app/types/nullable'

export interface CashForecastPointInterface {
  date: string
  balance: number
}

export interface CashGapInterface {
  date: string
  amount: number
}

export interface CashForecastOperationInterface {
  id: string
  date: string
  title: string
  amount: number
}

export interface CashForecastInterface {
  status: CashForecastStatusEnum
  horizonDays: number
  currency: string
  points: CashForecastPointInterface[]
  cashGap: Nullable<CashGapInterface>
  operations: CashForecastOperationInterface[]
}
