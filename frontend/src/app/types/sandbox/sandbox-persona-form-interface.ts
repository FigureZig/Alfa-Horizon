import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { Nullable } from '@/app/types/nullable'

export interface SandboxPersonaFormInterface {
  fullName: string
  inn: string
  organization: string
  form: LegalFormEnum
  okved: string
  okvedName: string
  ageMonths: Nullable<number>
  headcount: Nullable<number>
  inflowAvg: Nullable<number>
  inflowCv: Nullable<number>
  inflowTrend: Nullable<number>
  debtLoad: Nullable<number>
  overdueDays: Nullable<number>
  bkiRequests: Nullable<number>
  taxDebt: Nullable<number>
  participants: Nullable<number>
  profitMargin: Nullable<number>
  contractPrice: Nullable<number>
  flags: string[]
  code: string
  scenario: string
  permissions: string
  profile: string
  registries: string
  preview: string
  loginLabel: string
}
