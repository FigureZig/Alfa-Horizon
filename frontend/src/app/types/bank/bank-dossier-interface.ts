import type { Nullable } from '@/app/types/nullable'

export interface BankDossierFactsInterface {
  name: Nullable<string>
  inn: string
  segment: Nullable<string>
  okved: Nullable<string>
  okvedName: Nullable<string>
  registeredAt: Nullable<string>
  ageMonths: Nullable<number>
  headcount: Nullable<number>
  taxRegime: Nullable<string>
  taxDebt: Nullable<number>
  monthlyInflow: Nullable<number>
  inflowVariation: Nullable<number>
  debtLoad: Nullable<number>
  maxOverdueDays: Nullable<number>
  bkiRequests: Nullable<number>
  isBkiKnown: boolean
}

export interface BankDossierSourceInterface {
  source: string
  status: string
  fetchedAt: string
  isStale: boolean
}

export interface BankDossierInterface {
  facts: BankDossierFactsInterface
  sources: BankDossierSourceInterface[]
}
