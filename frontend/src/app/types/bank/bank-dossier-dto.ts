import type { ApplicationDto } from '@/app/types/application/application-dto'
import type { ApplicationEventDto } from '@/app/types/application/application-event-dto'
import type { Nullable } from '@/app/types/nullable'

export interface BankDossierFactsDto {
  name: Nullable<string>
  inn: string
  segment: Nullable<string>
  okved: Nullable<string>
  okved_name: Nullable<string>
  registered: Nullable<string>
  age_months: Nullable<number>
  headcount: Nullable<number>
  tax_regime: Nullable<string>
  tax_debt: Nullable<string>
  inflow_avg: Nullable<string>
  inflow_cv: Nullable<number>
  debt_load: Nullable<number>
  max_overdue_days: Nullable<number>
  bki_requests_30d: Nullable<number>
  bki_known: boolean
}

export interface BankDossierSourceDto {
  source: string
  status: string
  fetched_at: string
  stale: boolean
}

/**
 * Досье заявки: GET v1/bank/applications/{id}/dossier. Факты компании и откуда они взяты;
 * сверх DTO отдаются и остальные факты, и сама заявка с историей.
 */
export interface BankDossierDto {
  application: ApplicationDto
  facts: BankDossierFactsDto
  sources: BankDossierSourceDto[]
  events: ApplicationEventDto[]
}
