import type { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import type { ApplicationAskEnum } from '@/app/types/application/application-ask-enum'
import type { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'
import type { ApplicationVoteEnum } from '@/app/types/application/application-vote-enum'
import type { ApprovalStatusEnum } from '@/app/types/application/approval-status-enum'
import type { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { DecisionKindEnum } from '@/app/types/application/decision-kind-enum'
import type { DecisionOfferKindEnum } from '@/app/types/application/decision-offer-kind-enum'
import type { DecisionOutcomeEnum } from '@/app/types/application/decision-outcome-enum'
import type { SigningModeEnum } from '@/app/types/application/signing-mode-enum'
import type { BankNoteDto } from '@/app/types/bank/bank-note-dto'
import type { Nullable } from '@/app/types/nullable'

// Деньги и ставки в ядре API приходят строками («400000.00») — Decimal без потерь; число получает маппер

export interface ApplicationRequestDto {
  product: CreditProductCodeEnum
  amount: string
  term_months?: number
  goal?: CreditGoalEnum
}

export interface ApplicationRateDto {
  total: string
  key_rate: string
  industry: string
  risk: string
  risk_class: string
}

export interface ApplicationOfferDto {
  product: CreditProductCodeEnum
  product_name: string
  amount: string
  term_months: number
  payment: string
  repayment: string
  rate: ApplicationRateDto
  binding_cap: Nullable<string>
  variant?: Nullable<number>
}

export interface ApplicationReasonDto {
  code: string
  kind: string
  text: string
}

export interface ApplicationDecisionDto {
  outcome: DecisionOutcomeEnum
  // Вид отказа; у остальных решений — null
  kind?: Nullable<DecisionKindEnum>
  offer_kind: Nullable<DecisionOfferKindEnum>
  counter: string[]
  conditions: string[]
  asks: ApplicationAskEnum[]
  reasons: ApplicationReasonDto[]
  hints: string[]
}

export interface ApplicationInfoRequestDto {
  asks: ApplicationAskEnum[]
  from?: Nullable<string>
  comment?: Nullable<string>
}

export interface ApplicationSignersDto {
  mode: SigningModeEnum
  any_of: string[]
  required: string[]
}

export interface ApplicationSignatureDto {
  inn: string
  fio: string
  role: string
  at: string
}

export interface ApplicationParticipantDto {
  inn: string
  fio: string
  share: number
}

export interface ApplicationVoteDto {
  inn: string
  fio?: Nullable<string>
  vote: ApplicationVoteEnum
}

export interface ApplicationApprovalDto {
  status: ApprovalStatusEnum
  method: string
  participants: ApplicationParticipantDto[]
  votes: ApplicationVoteDto[]
  for_pct: number
  against_pct: number
  threshold_pct: number
}

export interface ApplicationLoanDto {
  // limit — лимит овердрафта подключён к счёту; loan — деньги зачислены
  kind?: 'limit' | 'loan'
  // Номер договора вида КД-2026/XXXXXX
  number?: string
  loan_id: string
  amount: string
  rate: string
  term_months: number
  status: string
  disbursed_at: string
}

export interface ApplicationDeadlineDto {
  status: ApplicationDetailStatusEnum
  at: string
  then: ApplicationDetailStatusEnum
}

/**
 * Заявка целиком: GET v1/applications, GET v1/applications/{id} и ответ каждой команды.
 * `available_actions` — кнопки, которые текущий пользователь может нажать сейчас: права и статус бэкенд уже учёл.
 */
export interface ApplicationCreatorDto {
  inn: string
  name: string
  persona: Nullable<string>
}

export interface ApplicationDto {
  id: string
  company_inn: string
  status: ApplicationDetailStatusEnum
  flags: ApplicationFlagEnum[]
  created_at: string
  updated_at: string
  // Кто подготовил заявку
  created_by?: Nullable<ApplicationCreatorDto>
  request: ApplicationRequestDto
  consent_bki: boolean
  decision: Nullable<ApplicationDecisionDto>
  offer: Nullable<ApplicationOfferDto>
  offers: ApplicationOfferDto[]
  info_request: Nullable<ApplicationInfoRequestDto>
  signers: Nullable<ApplicationSignersDto>
  signatures: ApplicationSignatureDto[]
  approval: Nullable<ApplicationApprovalDto>
  loan: Nullable<ApplicationLoanDto>
  deadline: Nullable<ApplicationDeadlineDto>
  sla_until: Nullable<string>
  pending_decision: Nullable<BankNoteDto>
  bank_decision: Nullable<BankNoteDto>
  available_actions: ApplicationActionEnum[]
}
