import type { DashboardSummaryCardTypeEnum } from '@/app/types/dashboard/dashboard-summary-card-type-enum'

export interface DashboardSummaryCardInterface {
  id: string
  type: DashboardSummaryCardTypeEnum
  title: string
  amount: number
  currency: string
  description: string
}
