import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { Nullable } from '@/app/types/nullable'
import type { CompanyProfileDto } from '@/app/types/company/company-profile-dto'
import { DataSourceEnum } from '@/app/types/company/data-source-enum'
import { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import { TaxRegimeEnum } from '@/app/types/company/tax-regime-enum'
import { hasDemoPersonaMock } from '@/app/mocks/demo-persona'
import {
  getInnFromUrl,
  getMockIsoDateTime,
  rejectMockNotFound,
  resolveMockResponse,
} from '@/app/mocks/mock-response'

interface CompanyProfileMock {
  legalForm: Nullable<LegalFormEnum>
  registeredAt: Nullable<string>
  activity: Nullable<{ okvedCode: string, name: Record<AppLocale, string> }>
  taxRegime: Nullable<TaxRegimeEnum>
  monthlyRevenue: Nullable<number>
  sources: DataSourceEnum[]
  // Когда сведения обновлялись: дней назад, часы, минуты
  updated: Nullable<[daysAgo: number, hours: number, minutes: number]>
}

const MOCK_CURRENCY = 'RUB'

/**
 * Что банк знает о компании, по ИНН. Компании без записи (банк, новые персоны) — без сведений.
 */
const companyProfileMock: Record<string, CompanyProfileMock> = {
  // Анна Смирнова — все сведения заполнены
  '770100000079': {
    legalForm: LegalFormEnum.SoleProprietor,
    registeredAt: '2024-10-15',
    activity: { okvedCode: '56.30', name: { ru: 'Кофейня', en: 'Coffee shop' } },
    taxRegime: TaxRegimeEnum.Usn,
    monthlyRevenue: 1500000,
    sources: [DataSourceEnum.Egrul, DataSourceEnum.Fns, DataSourceEnum.BankAccount],
    updated: [1, 14, 2],
  },
  '7701000019': {
    legalForm: LegalFormEnum.Llc,
    registeredAt: '2022-03-10',
    activity: { okvedCode: '46.90', name: { ru: 'Оптовая торговля', en: 'Wholesale trade' } },
    taxRegime: TaxRegimeEnum.Osn,
    monthlyRevenue: 12000000,
    sources: [DataSourceEnum.Egrul, DataSourceEnum.Fns, DataSourceEnum.BankAccount, DataSourceEnum.CreditBureau],
    updated: [0, 9, 15],
  },
  '7701000026': {
    legalForm: LegalFormEnum.Llc,
    registeredAt: '2019-06-04',
    activity: { okvedCode: '41.20', name: { ru: 'Строительство зданий', en: 'Building construction' } },
    taxRegime: TaxRegimeEnum.Osn,
    monthlyRevenue: 4200000,
    sources: [DataSourceEnum.Egrul, DataSourceEnum.Fns],
    updated: [2, 18, 40],
  },
  // Игорь Белов — оборот неизвестен: бейдж не показывается
  '7701000033': {
    legalForm: LegalFormEnum.Llc,
    registeredAt: '2021-02-01',
    activity: { okvedCode: '81.21', name: { ru: 'Уборка помещений', en: 'Cleaning services' } },
    taxRegime: TaxRegimeEnum.Usn,
    monthlyRevenue: null,
    sources: [DataSourceEnum.Egrul, DataSourceEnum.Fns],
    updated: [0, 8, 5],
  },
  // Иван Иванов — налоговый режим неизвестен
  '7701000040': {
    legalForm: LegalFormEnum.Llc,
    registeredAt: '2022-09-20',
    activity: { okvedCode: '10.71', name: { ru: 'Пекарня', en: 'Bakery' } },
    taxRegime: null,
    monthlyRevenue: 2800000,
    sources: [DataSourceEnum.Egrul, DataSourceEnum.BankAccount],
    updated: [1, 10, 47],
  },
  '7701000065': {
    legalForm: LegalFormEnum.Llc,
    registeredAt: '2019-11-12',
    activity: { okvedCode: '46.39', name: { ru: 'Оптовая торговля продуктами', en: 'Food wholesale' } },
    taxRegime: TaxRegimeEnum.Ausn,
    monthlyRevenue: 6000000,
    sources: [DataSourceEnum.Egrul, DataSourceEnum.Fns, DataSourceEnum.BankAccount],
    updated: [0, 12, 20],
  },
}

/**
 * Axios-адаптер для GET v1/companies/{inn}/profile (предлагаемый контракт).
 */
export function companyProfileMockAdapter(
  config: InternalAxiosRequestConfig,
): Promise<AxiosResponse<ApiResponse<CompanyProfileDto>>> {
  const locale: AppLocale = config.params?.lang === 'en' ? 'en' : 'ru'
  const inn = getInnFromUrl(config.url)

  if (!hasDemoPersonaMock(inn)) {
    return rejectMockNotFound(config)
  }

  const profile = companyProfileMock[inn]

  return resolveMockResponse(config, {
    data: {
      inn,
      legal_form: profile?.legalForm ?? null,
      registered_at: profile?.registeredAt ?? null,
      activity: profile?.activity
        ? { okved_code: profile.activity.okvedCode, name: profile.activity.name[locale] }
        : null,
      tax_regime: profile?.taxRegime ?? null,
      monthly_revenue: profile?.monthlyRevenue ?? null,
      currency: MOCK_CURRENCY,
      sources: profile?.sources ?? [],
      updated_at: profile?.updated ? getMockIsoDateTime(-profile.updated[0], profile.updated[1], profile.updated[2]) : null,
    },
  })
}
