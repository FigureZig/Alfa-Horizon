import type { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import type { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'
import type {
  ApplicationOfferInterface,
  ApplicationReasonInterface,
  ApplicationRequestInterface,
} from '@/app/types/application/application-interface'
import type { BankNoteInterface } from '@/app/types/bank/bank-note-interface'
import type { Nullable } from '@/app/types/nullable'

export interface BankQueueItemInterface {
  id: string
  inn: string
  status: ApplicationDetailStatusEnum
  flags: ApplicationFlagEnum[]
  request: ApplicationRequestInterface
  reasons: ApplicationReasonInterface[]
  proposal: Nullable<ApplicationOfferInterface>
  score: Nullable<number>
  riskClass: Nullable<string>
  pendingDecision: Nullable<BankNoteInterface>
  availableActions: ApplicationActionEnum[]
  slaUntil: Nullable<string>
  updatedAt: string
}
