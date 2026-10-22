import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { CreditProductDto } from '@/app/types/company/credit-product-dto'
import { hasDemoPersonaMock } from '@/app/mocks/demo-persona'
import {
  getInnFromUrl,
  rejectMockNotFound,
  resolveMockResponse,
} from '@/app/mocks/mock-response'

interface CreditProductMock {
  id: string
  name: Record<AppLocale, string>
  amount: number
  rate: number
  isRateFrom: boolean
  termMonths: number
  benefits: Record<AppLocale, string[]>
  isPreliminary: boolean
  isRecommended: boolean
}

const MOCK_CURRENCY = 'RUB'

const OVERDRAFT_BENEFITS: Record<AppLocale, string[]> = {
  ru: [
    'Деньги на счёте через 5 минут после подписи',
    'Гасится автоматически из поступлений',
    'Без залога и поручителей',
  ],
  en: [
    'Funds in your account 5 minutes after signing',
    'Repaid automatically from incoming payments',
    'No collateral or guarantors',
  ],
}

/**
 * Предодобренные продукты (K2) по ИНН. Компании без записи получают пустой список.
 * `isRecommended` — продукт, который закрывает найденный кассовый разрыв.
 */
const creditProductsMock: Record<string, CreditProductMock[]> = {
  // Анна Смирнова — два предодобренных продукта
  '770100000079': [
    {
      id: 'overdraft-770100000079',
      name: { ru: 'Овердрафт', en: 'Overdraft' },
      amount: 600000,
      rate: 17.6,
      isRateFrom: false,
      termMonths: 12,
      benefits: OVERDRAFT_BENEFITS,
      isPreliminary: true,
      isRecommended: true,
    },
    {
      id: 'express-loan-770100000079',
      name: { ru: 'Экспресс-кредит', en: 'Express loan' },
      amount: 4000000,
      rate: 17.6,
      isRateFrom: true,
      termMonths: 36,
      benefits: {
        ru: ['Решение онлайн', 'Без залога'],
        en: ['Online decision', 'No collateral'],
      },
      isPreliminary: true,
      isRecommended: false,
    },
  ],
  // Павел Орлов — разрыва нет, продукт есть
  '7701000019': [
    {
      id: 'secured-loan-7701000019',
      name: { ru: 'Кредит под залог недвижимости', en: 'Real estate secured loan' },
      amount: 15000000,
      rate: 19.5,
      isRateFrom: true,
      termMonths: 36,
      benefits: {
        ru: ['Сумма выше за счёт залога', 'Срок до 3 лет'],
        en: ['Higher amount thanks to collateral', 'Up to 3 years'],
      },
      isPreliminary: false,
      isRecommended: false,
    },
  ],
  // Елена Кравец — разрыв есть, но подходящего предложения нет: нужно решение участников
  '7701000026': [
    {
      id: 'contract-loan-7701000026',
      name: { ru: 'Кредит под исполнение контракта', en: 'Contract execution loan' },
      amount: 25000000,
      rate: 18,
      isRateFrom: true,
      termMonths: 18,
      benefits: {
        ru: ['Под выручку по контракту', 'Требуется решение участников'],
        en: ['Backed by contract revenue', 'Members’ approval required'],
      },
      isPreliminary: true,
      isRecommended: false,
    },
  ],
  // Иван Иванов — один продукт
  '7701000040': [
    {
      id: 'credit-line-7701000040',
      name: { ru: 'Возобновляемая кредитная линия', en: 'Revolving credit line' },
      amount: 500000,
      rate: 19.5,
      isRateFrom: false,
      termMonths: 12,
      benefits: {
        ru: [
          'Берёте только нужную сумму',
          'Проценты только за фактическое использование',
          'Лимит восстанавливается после погашения',
        ],
        en: [
          'Draw only the amount you need',
          'Interest only on what you use',
          'The limit is restored after repayment',
        ],
      },
      isPreliminary: false,
      isRecommended: true,
    },
  ],
}

/**
 * Axios-адаптер для GET v1/companies/{inn}/products.
 */
export function companyProductsMockAdapter(
  config: InternalAxiosRequestConfig,
): Promise<AxiosResponse<ApiResponse<CreditProductDto[]>>> {
  const locale: AppLocale = config.params?.lang === 'en' ? 'en' : 'ru'
  const inn = getInnFromUrl(config.url)

  if (!hasDemoPersonaMock(inn)) {
    return rejectMockNotFound(config)
  }

  const products = (creditProductsMock[inn] ?? []).map((product) => ({
    id: product.id,
    name: product.name[locale],
    amount: product.amount,
    currency: MOCK_CURRENCY,
    rate: product.rate,
    is_rate_from: product.isRateFrom,
    term_months: product.termMonths,
    benefits: product.benefits[locale],
    is_preliminary: product.isPreliminary,
    is_recommended: product.isRecommended,
  }))

  return resolveMockResponse(config, { data: products })
}
