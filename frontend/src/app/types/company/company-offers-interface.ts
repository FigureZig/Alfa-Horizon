import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { CompanyBlockerInterface } from '@/app/types/company/company-blocker-interface'
import type { Nullable } from '@/app/types/nullable'

export interface CompanyOfferOptionInterface {
  code: CreditProductCodeEnum
  name: string
  isAvailable: boolean
  // Порядок группы: доступен, с условиями, у специалиста, не подходит
  rank: number
  // Подпись состояния: PREAPPROVED · CONDITIONAL · REVIEW · UNAVAILABLE
  label: string
  isRevolving: boolean
  maxAmount: Nullable<number>
  // Условия под заданные сумму и срок; без них — личные условия на максимум
  amount: Nullable<number>
  termMonths: Nullable<number>
  rate: Nullable<number>
  payment: Nullable<number>
  needs: string[]
  reasons: string[]
  isRecommended: boolean
}

export interface CompanyOffersInterface {
  blockers: CompanyBlockerInterface[]
  options: CompanyOfferOptionInterface[]
}
