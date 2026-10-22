import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { DashboardSummaryCardDto } from '@/app/types/dashboard/dashboard-summary-card-dto'
import { DashboardSummaryCardTypeEnum } from '@/app/types/dashboard/dashboard-summary-card-type-enum'
import { hasDemoPersonaMock } from '@/app/mocks/demo-persona'
import {
  getInnFromUrl,
  rejectMockNotFound,
  resolveMockResponse,
} from '@/app/mocks/mock-response'

interface DashboardSummaryCardMock {
  id: string
  type: DashboardSummaryCardTypeEnum
  amount: number
  // Через сколько дней наступает дата карточки (для списаний и поступлений)
  daysAhead: number
  description: Record<AppLocale, string>
}

const MOCK_CURRENCY = 'RUB'

/**
 * Данные GET v1/demo-personas/:inn/dashboard/summary по ИНН компании.
 * Количество карточек у персон разное: так проверяется динамическая отрисовка.
 */
const dashboardSummaryMock: Record<string, DashboardSummaryCardMock[]> = {
  // S7
  '770100000079': [
    {
      id: 's7-balance',
      type: DashboardSummaryCardTypeEnum.Balance,
      amount: 184300,
      daysAhead: 0,
      description: { ru: 'Расчётный счёт ·· 4821', en: 'Current account ·· 4821' },
    },
    {
      id: 's7-outflow',
      type: DashboardSummaryCardTypeEnum.Outflow,
      amount: 412000,
      daysAhead: 9,
      description: { ru: 'Аренда, закупка зерна и зарплата', en: 'Rent, coffee beans, and payroll' },
    },
    {
      id: 's7-inflow',
      type: DashboardSummaryCardTypeEnum.Inflow,
      amount: 268500,
      daysAhead: 9,
      description: { ru: 'Эквайринг и оплаты от корпоративных клиентов', en: 'Card acquiring and corporate client payments' },
    },
  ],
  // S3
  '7701000019': [
    {
      id: 's3-balance',
      type: DashboardSummaryCardTypeEnum.Balance,
      amount: 3920000,
      daysAhead: 0,
      description: { ru: 'Расчётный счёт ·· 0457', en: 'Current account ·· 0457' },
    },
    {
      id: 's3-outflow',
      type: DashboardSummaryCardTypeEnum.Outflow,
      amount: 2750000,
      daysAhead: 14,
      description: { ru: 'Платёж по кредиту, поставщики и налоги', en: 'Loan payment, suppliers, and taxes' },
    },
    {
      id: 's3-inflow',
      type: DashboardSummaryCardTypeEnum.Inflow,
      amount: 4100000,
      daysAhead: 14,
      description: { ru: 'Оплаты покупателей по договорам поставки', en: 'Customer payments under supply contracts' },
    },
  ],
  // S2
  '7701000026': [
    {
      id: 's2-balance',
      type: DashboardSummaryCardTypeEnum.Balance,
      amount: 1260000,
      daysAhead: 0,
      description: { ru: 'Расчётный счёт ·· 7310', en: 'Current account ·· 7310' },
    },
    {
      id: 's2-inflow',
      type: DashboardSummaryCardTypeEnum.Inflow,
      amount: 5800000,
      daysAhead: 20,
      description: { ru: 'Авансы по договорам подряда', en: 'Advances under construction contracts' },
    },
  ],
  // S4
  '7701000033': [
    {
      id: 's4-balance',
      type: DashboardSummaryCardTypeEnum.Balance,
      amount: 640000,
      daysAhead: 0,
      description: { ru: 'Расчётный счёт ·· 2209', en: 'Current account ·· 2209' },
    },
  ],
  // R8
  '7701000040': [
    {
      id: 'r8-balance',
      type: DashboardSummaryCardTypeEnum.Balance,
      amount: 975400,
      daysAhead: 0,
      description: { ru: 'Расчётный счёт ·· 1184', en: 'Current account ·· 1184' },
    },
    {
      id: 'r8-outflow',
      type: DashboardSummaryCardTypeEnum.Outflow,
      amount: 530000,
      daysAhead: 7,
      description: { ru: 'Зарплата и страховые взносы', en: 'Payroll and social contributions' },
    },
    {
      id: 'r8-inflow',
      type: DashboardSummaryCardTypeEnum.Inflow,
      amount: 720000,
      daysAhead: 7,
      description: { ru: 'Оплаты по договорам оказания услуг', en: 'Payments under service contracts' },
    },
  ],
  // R12
  '7701000065': [
    {
      id: 'r12-balance',
      type: DashboardSummaryCardTypeEnum.Balance,
      amount: 2310000,
      daysAhead: 0,
      description: { ru: 'Расчётный счёт ·· 6642', en: 'Current account ·· 6642' },
    },
    {
      id: 'r12-outflow',
      type: DashboardSummaryCardTypeEnum.Outflow,
      amount: 1480000,
      daysAhead: 10,
      description: { ru: 'Поставщики и логистика', en: 'Suppliers and logistics' },
    },
  ],
  // Fino Банк (кредитный специалист): своих счетов нет — блок карточек не показывается
  '7701000097': [],
}

const TITLE_TEMPLATES: Record<AppLocale, Record<DashboardSummaryCardTypeEnum, string>> = {
  ru: {
    [DashboardSummaryCardTypeEnum.Balance]: 'На счёте сегодня',
    [DashboardSummaryCardTypeEnum.Outflow]: 'Списания до {date}',
    [DashboardSummaryCardTypeEnum.Inflow]: 'Поступления до {date}',
  },
  en: {
    [DashboardSummaryCardTypeEnum.Balance]: 'Balance today',
    [DashboardSummaryCardTypeEnum.Outflow]: 'Outflows until {date}',
    [DashboardSummaryCardTypeEnum.Inflow]: 'Inflows until {date}',
  },
}

function buildTitle(card: DashboardSummaryCardMock, locale: AppLocale): string {
  const date = new Date()
  date.setDate(date.getDate() + card.daysAhead)

  const formattedDate = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long' }).format(date)

  return TITLE_TEMPLATES[locale][card.type].replace('{date}', formattedDate)
}

/**
 * Axios-адаптер для GET v1/demo-personas/:inn/dashboard/summary.
 * Заголовки и даты собираются на «бэкенде» на языке из параметра `lang`.
 */
export function dashboardSummaryMockAdapter(
  config: InternalAxiosRequestConfig,
): Promise<AxiosResponse<ApiResponse<DashboardSummaryCardDto[]>>> {
  const locale: AppLocale = config.params?.lang === 'en' ? 'en' : 'ru'
  const inn = getInnFromUrl(config.url)

  if (!hasDemoPersonaMock(inn)) {
    return rejectMockNotFound(config)
  }

  const cards = (dashboardSummaryMock[inn] ?? []).map((card) => ({
    id: card.id,
    type: card.type,
    title: buildTitle(card, locale),
    amount: card.amount,
    currency: MOCK_CURRENCY,
    description: card.description[locale],
  }))

  return resolveMockResponse(config, { data: cards })
}
