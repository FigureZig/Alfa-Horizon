import type { BankDecisionActionEnum } from '@/app/types/bank/bank-decision-action-enum'

/**
 * Тело POST v1/bank/applications/{id}/decision: одобрить (возможно, другую сумму и срок по той же цене риска),
 * отказать или запросить у клиента данные.
 */
export interface BankDecisionDto {
  action: BankDecisionActionEnum
  amount?: number
  term_months?: number
  comment?: string
  asks?: string[]
}

/** Тело POST v1/bank/applications/{id}/decision/confirm — второй ключ риск-менеджера. */
export interface BankConfirmDto {
  approve: boolean
  comment?: string
}
