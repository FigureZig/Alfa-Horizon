import type { DataSourceEnum } from '@/app/types/company/data-source-enum'
import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { TaxRegimeEnum } from '@/app/types/company/tax-regime-enum'
import type { Nullable } from '@/app/types/nullable'

export interface CompanyActivityDto {
  okved_code: string
  name: Nullable<string>
  // Коротко, по-человечески: «Пекарня, хлебозавод»
  title?: Nullable<string>
}

// Руководитель по ЕГРЮЛ/ЕГРИП: по ИНН подписи заявки видно, кого ждём
export interface CompanyDirectorDto {
  inn: string
  fio: string
  title: string
}

/**
 * Ответ GET v1/companies/{inn}/profile — что банк знает о компании.
 * Любое поле может быть null. Сверх DTO API отдаёт name, msp_category, headcount, facts, source_details.
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
  // Все факты компании; нужен только раздел ОКВЭД (`section`) для расчёта ставки
  facts: { section?: Nullable<string>, eio?: CompanyDirectorDto[] }
}
