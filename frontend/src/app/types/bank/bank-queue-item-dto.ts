import type { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'
import type { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import type { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { ApplicationOfferDto, ApplicationReasonDto, ApplicationRequestDto } from '@/app/types/application/application-dto'
import type { BankNoteDto } from '@/app/types/bank/bank-note-dto'
import type { Nullable } from '@/app/types/nullable'

export interface BankQueueRiskDto {
  score: number
  pd: number
  class: string
}

/**
 * Заявка в очереди: GET v1/bank/queue. Причины — только те, что привели к ручному рассмотрению;
 * `proposal` — условия, которые предложил бы движок.
 */
export interface BankQueueItemDto {
  id: string
  inn: string
  status: ApplicationDetailStatusEnum
  flags: ApplicationFlagEnum[]
  request: ApplicationRequestDto
  reasons: ApplicationReasonDto[]
  proposal: Nullable<ApplicationOfferDto>
  risk: Nullable<BankQueueRiskDto>
  pending_decision: Nullable<BankNoteDto>
  available_actions: ApplicationActionEnum[]
  sla_until: Nullable<string>
  updated_at: string
}
