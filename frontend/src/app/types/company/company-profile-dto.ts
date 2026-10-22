import type { DataSourceEnum } from '@/app/types/company/data-source-enum'
import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { TaxRegimeEnum } from '@/app/types/company/tax-regime-enum'
import type { Nullable } from '@/app/types/nullable'

export interface CompanyActivityDto {
  okved_code: string
  name: string
}

/**
 * Ответ GET v1/companies/{inn}/profile — что банк знает о компании.
 * Предлагаемый контракт — согласовать с бэкендом. Любое поле может отсутствовать.
 */
export interface CompanyProfileDto {
  inn: string
  legal_form: Nullable<LegalFormEnum>
  registered_at: Nullable<string>
  activity: Nullable<CompanyActivityDto>
  tax_regime: Nullable<TaxRegimeEnum>
  monthly_revenue: Nullable<number>
  currency: string
  sources: DataSourceEnum[]
  updated_at: Nullable<string>
}
