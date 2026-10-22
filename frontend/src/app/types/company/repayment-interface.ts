import type { RepaymentRecommendationEnum } from '@/app/types/company/repayment-recommendation-enum'

export interface RepaymentInterface {
  fixedPayment: number
  fixedTotalInterest: number
  fixedWorstShare: number
  isFixedComfortable: boolean
  inflowShare: number
  inflowMinPayment: number
  inflowMaxPayment: number
  inflowMonths: number
  inflowTotalInterest: number
  recommendation: RepaymentRecommendationEnum
  why: string
}
