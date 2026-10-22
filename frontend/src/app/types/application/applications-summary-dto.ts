import type { ApplicationStatusEnum } from '@/app/types/application/application-status-enum'
import type { TaskTypeEnum } from '@/app/types/application/task-type-enum'
import type { Nullable } from '@/app/types/nullable'

export interface ApplicationSummaryItemDto {
  id: string
  product_name: string
  amount: number
  currency: string
  status: ApplicationStatusEnum
  updated_at: string
}

export interface TaskDto {
  id: string
  type: TaskTypeEnum
  title: string
  due_date: Nullable<string>
  application_id: Nullable<string>
}

/**
 * Ответ GET v1/companies/{inn}/applications/summary. Заявки и задачи — независимые списки.
 * `due_date` у задачи — дата со временем (ISO 8601). Сверх DTO API отдаёт status_detail, flags, all_tasks.
 */
export interface ApplicationsSummaryDto {
  applications: ApplicationSummaryItemDto[]
  tasks: TaskDto[]
}
