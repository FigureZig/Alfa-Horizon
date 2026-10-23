import type { ApplicationTaskDto } from '@/app/types/application/application-task-dto'
import type { ApplicationTaskInterface } from '@/app/types/application/application-task-interface'

export class ApplicationTaskMapper {
  static toEntity(data: ApplicationTaskDto): ApplicationTaskInterface {
    if (!data) {
      throw new Error('Application task data is required')
    }

    return {
      id: data.id,
      action: data.action,
      title: data.title,
      dueDate: data.due_date,
      applicationId: data.application_id,
      companyInn: data.company_inn,
    }
  }
}
