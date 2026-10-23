import type { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'
import type { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { DecisionOutcomeEnum } from '@/app/types/application/decision-outcome-enum'
import type { BankDecidedByEnum } from '@/app/types/bank/bank-decided-by-enum'
import type { Nullable } from '@/app/types/nullable'

/**
 * Строка реестра заявок банка: GET v1/bank/applications. `decided_by: null` — решения ещё нет
 * (заявка на ручном рассмотрении); `company_name` сохраняется при подаче и переживает удаление своей компании.
 */
export interface BankApplicationDto {
  id: string
  inn: string
  company_name: Nullable<string>
  status: ApplicationDetailStatusEnum
  flags: ApplicationFlagEnum[]
  request: { product: CreditProductCodeEnum, amount: string, term_months?: number }
  outcome: Nullable<DecisionOutcomeEnum>
  decided_by: Nullable<BankDecidedByEnum>
  offer: Nullable<{ amount: string, product_name: string }>
  score: Nullable<number>
  risk_class: Nullable<string>
  created_at: string
  updated_at: string
}
