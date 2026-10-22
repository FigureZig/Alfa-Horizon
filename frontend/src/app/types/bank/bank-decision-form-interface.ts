import type { ApplicationAskEnum } from '@/app/types/application/application-ask-enum'
import type { BankDecisionActionEnum } from '@/app/types/bank/bank-decision-action-enum'
import type { Nullable } from '@/app/types/nullable'

export interface BankDecisionFormInterface {
  action: BankDecisionActionEnum
  amount: Nullable<number>
  termMonths: Nullable<number>
  asks: ApplicationAskEnum[]
  comment: string
}

export interface BankConfirmFormInterface {
  isApproved: boolean
  comment: string
}
