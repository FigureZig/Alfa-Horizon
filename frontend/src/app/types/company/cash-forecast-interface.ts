import type { CashForecastStatusEnum } from '@/app/types/company/cash-forecast-status-enum'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'
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

export interface CashForecastRegularOutflowInterface {
  title: string
  day: number
  amount: number
}

export interface CashGapCoverInterface {
  amount: number
  days: number
  interest: number
}

// Предложение под разрыв: продукт с ценой закрытия разрыва
export interface CashGapOfferInterface extends CreditProductInterface {
  cover: Nullable<CashGapCoverInterface>
}

export interface CompanyContractInterface {
  regNum: string
  customer: string
  price: number
  advancePercent: Nullable<number>
  endDate: Nullable<string>
}

export interface CashForecastInterface {
  status: CashForecastStatusEnum
  horizonDays: number
  currency: string
  points: CashForecastPointInterface[]
  cashGap: Nullable<CashGapInterface>
  creditLine: Nullable<number>
  dailyInflow: Nullable<number>
  regularOutflows: CashForecastRegularOutflowInterface[]
  offer: Nullable<CashGapOfferInterface>
  contract: Nullable<CompanyContractInterface>
  operations: CashForecastOperationInterface[]
}
