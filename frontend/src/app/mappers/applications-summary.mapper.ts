import type { ApplicationsSummaryDto } from '@/app/types/application/applications-summary-dto'
import type { ApplicationsSummaryInterface } from '@/app/types/application/applications-summary-interface'

export class ApplicationsSummaryMapper {
  static toEntity(data: ApplicationsSummaryDto): ApplicationsSummaryInterface {
    if (!data) {
      throw new Error('Applications summary data is required')
    }

    return {
      applications: data.applications.map((application) => ({
        id: application.id,
        productName: application.product_name,
        amount: application.amount,
        currency: application.currency,
        status: application.status,
        statusDetail: application.status_detail,
        updatedAt: application.updated_at,
      })),
      tasks: data.tasks.map((task) => ({
        id: task.id,
        type: task.type,
        action: task.action ?? null,
        title: task.title,
        dueDate: task.due_date,
        applicationId: task.application_id,
      })),
    }
  }
}
