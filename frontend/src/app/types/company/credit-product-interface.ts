import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'

export interface CreditProductInterface {
  id: string
  code: CreditProductCodeEnum
  name: string
  amount: number
  currency: string
  rate: number
  isRateFrom: boolean
  termMonths: number
  benefits: string[]
  isPreliminary: boolean
  isRecommended: boolean
}
