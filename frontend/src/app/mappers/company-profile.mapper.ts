import type { CompanyProfileDto } from '@/app/types/company/company-profile-dto'
import type { CompanyProfileInterface } from '@/app/types/company/company-profile-interface'

export class CompanyProfileMapper {
  static toEntity(data: CompanyProfileDto): CompanyProfileInterface {
    if (!data) {
      throw new Error('Company profile data is required')
    }

    return {
      legalForm: data.legal_form,
      registeredAt: data.registered_at,
      activity: data.activity
        ? { okvedCode: data.activity.okved_code, name: data.activity.name }
        : null,
      taxRegime: data.tax_regime,
      monthlyRevenue: data.monthly_revenue,
      currency: data.currency,
      sources: data.sources,
      updatedAt: data.updated_at,
      section: data.facts?.section ?? null,
    }
  }
}
