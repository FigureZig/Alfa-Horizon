import type { DashboardSummaryCardDto } from '@/app/types/dashboard/dashboard-summary-card-dto'
import type { DashboardSummaryCardInterface } from '@/app/types/dashboard/dashboard-summary-card-interface'

export class DashboardMapper {
  static toEntity(data: DashboardSummaryCardDto): DashboardSummaryCardInterface {
    if (!data) {
      throw new Error('Dashboard summary card data is required')
    }

    return {
      id: data.id,
      type: data.type,
      title: data.title,
      amount: data.amount,
      currency: data.currency,
      description: data.description,
    }
  }
}
