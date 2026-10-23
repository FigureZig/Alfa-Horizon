import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { Nullable } from '@/app/types/nullable'

/** Ответы конструктора своей компании: простые вопросы и необязательные точные цифры. */
export interface SandboxPersonaFormInterface {
  fullName: string
  organization: string
  form: LegalFormEnum
  industry: Nullable<string>
  structure: Nullable<string>
  accountant: boolean
  representative: boolean
  seasonality: Nullable<string>
  stability: Nullable<string>
  trend: Nullable<string>
  channel: Nullable<string>
  loans: Nullable<string>
  delays: Nullable<string>
  ageMonths: Nullable<number>
  headcount: Nullable<number>
  inflowAvg: Nullable<number>
  flags: string[]
  // Точные цифры: пустые бэкенд выводит из простых ответов
  inn: string
  inflowCv: Nullable<number>
  inflowTrend: Nullable<number>
  debtLoad: Nullable<number>
  overdueDays: Nullable<number>
  bkiRequests: Nullable<number>
  taxDebt: Nullable<number>
  participants: Nullable<number>
  profitMargin: Nullable<number>
  contractPrice: Nullable<number>
}
