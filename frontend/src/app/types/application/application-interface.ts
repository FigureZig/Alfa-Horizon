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
import type { BankNoteInterface } from '@/app/types/bank/bank-note-interface'
import type { Nullable } from '@/app/types/nullable'

export interface ApplicationRequestInterface {
  product: CreditProductCodeEnum
  amount: number
  termMonths: Nullable<number>
  goal: Nullable<CreditGoalEnum>
}

export interface ApplicationOfferInterface {
  product: CreditProductCodeEnum
  productName: string
  amount: number
  termMonths: number
  payment: number
  repayment: string
  rate: number
  riskClass: string
  variant: Nullable<number>
}

export interface ApplicationReasonInterface {
  code: string
  kind: string
  text: string
}

export interface ApplicationDecisionInterface {
  outcome: DecisionOutcomeEnum
  kind: Nullable<DecisionKindEnum>
  offerKind: Nullable<DecisionOfferKindEnum>
  counter: string[]
  conditions: string[]
  asks: ApplicationAskEnum[]
  reasons: ApplicationReasonInterface[]
  hints: string[]
}

export interface ApplicationInfoRequestInterface {
  asks: ApplicationAskEnum[]
  comment: Nullable<string>
}

export interface ApplicationSignersInterface {
  mode: SigningModeEnum
  anyOf: string[]
  required: string[]
}

export interface ApplicationSignatureInterface {
  inn: string
  fio: string
  role: string
  at: string
}

export interface ApplicationParticipantInterface {
  inn: string
  fio: string
  share: number
}

export interface ApplicationVoteInterface {
  inn: string
  fio: Nullable<string>
  vote: ApplicationVoteEnum
}

export interface ApplicationApprovalInterface {
  status: ApprovalStatusEnum
  participants: ApplicationParticipantInterface[]
  votes: ApplicationVoteInterface[]
  forPercent: number
  againstPercent: number
  thresholdPercent: number
}

export interface ApplicationLoanInterface {
  isLimit: boolean
  // Номер договора; у кредитов, выданных до появления номеров, его нет
  number: Nullable<string>
  loanId: string
  amount: number
  rate: number
  termMonths: number
  disbursedAt: string
}

export interface ApplicationDeadlineInterface {
  status: ApplicationDetailStatusEnum
  at: string
  then: ApplicationDetailStatusEnum
}

export interface ApplicationCreatorInterface {
  inn: string
  name: string
}

export interface ApplicationInterface {
  id: string
  companyInn: string
  status: ApplicationDetailStatusEnum
  flags: ApplicationFlagEnum[]
  createdAt: string
  updatedAt: string
  createdBy: Nullable<ApplicationCreatorInterface>
  request: ApplicationRequestInterface
  consentBki: boolean
  decision: Nullable<ApplicationDecisionInterface>
  offer: Nullable<ApplicationOfferInterface>
  offers: ApplicationOfferInterface[]
  infoRequest: Nullable<ApplicationInfoRequestInterface>
  signers: Nullable<ApplicationSignersInterface>
  signatures: ApplicationSignatureInterface[]
  approval: Nullable<ApplicationApprovalInterface>
  loan: Nullable<ApplicationLoanInterface>
  deadline: Nullable<ApplicationDeadlineInterface>
  slaUntil: Nullable<string>
  pendingDecision: Nullable<BankNoteInterface>
  bankDecision: Nullable<BankNoteInterface>
  availableActions: ApplicationActionEnum[]
}
