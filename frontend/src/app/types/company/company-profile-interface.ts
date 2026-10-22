import type { DataSourceEnum } from '@/app/types/company/data-source-enum'
import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { TaxRegimeEnum } from '@/app/types/company/tax-regime-enum'
import type { Nullable } from '@/app/types/nullable'

export interface CompanyActivityInterface {
  okvedCode: string
  name: string
}

export interface CompanyProfileInterface {
  legalForm: Nullable<LegalFormEnum>
  registeredAt: Nullable<string>
  activity: Nullable<CompanyActivityInterface>
  taxRegime: Nullable<TaxRegimeEnum>
  monthlyRevenue: Nullable<number>
  currency: string
  sources: DataSourceEnum[]
  updatedAt: Nullable<string>
}
