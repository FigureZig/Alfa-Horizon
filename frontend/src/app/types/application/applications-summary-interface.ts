import type { ApplicationStatusEnum } from '@/app/types/application/application-status-enum'
import type { TaskTypeEnum } from '@/app/types/application/task-type-enum'
import type { Nullable } from '@/app/types/nullable'

export interface ApplicationSummaryItemInterface {
  id: string
  productName: string
  amount: number
  currency: string
  status: ApplicationStatusEnum
  updatedAt: string
}

export interface TaskInterface {
  id: string
  type: TaskTypeEnum
  title: string
  dueDate: Nullable<string>
  applicationId: Nullable<string>
}

export interface ApplicationsSummaryInterface {
  applications: ApplicationSummaryItemInterface[]
  tasks: TaskInterface[]
}
