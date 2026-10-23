import type { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { DecisionOutcomeEnum } from '@/app/types/application/decision-outcome-enum'
import type { BankDecidedByEnum } from '@/app/types/bank/bank-decided-by-enum'
import type { Nullable } from '@/app/types/nullable'

export interface BankApplicationInterface {
  id: string
  inn: string
  companyName: Nullable<string>
  status: ApplicationDetailStatusEnum
  product: CreditProductCodeEnum
  // Сумма по решению банка, если оно есть, иначе запрошенная
  amount: number
  outcome: Nullable<DecisionOutcomeEnum>
  decidedBy: Nullable<BankDecidedByEnum>
  riskClass: Nullable<string>
  updatedAt: string
}

/** Фильтры реестра: пустое значение — без фильтра. */
export interface BankApplicationsFilterInterface {
  status: Nullable<ApplicationDetailStatusEnum>
  decidedBy: Nullable<BankDecidedByEnum>
  query: string
}
