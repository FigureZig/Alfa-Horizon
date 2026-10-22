import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { CompanyInsightsDto } from '@/app/types/company/company-insights-dto'
import type {
  CashForecastDto,
  CashForecastOperationDto,
  CashForecastPointDto,
} from '@/app/types/company/cash-forecast-dto'
import { CashForecastStatusEnum } from '@/app/types/company/cash-forecast-status-enum'
import { hasDemoPersonaMock } from '@/app/mocks/demo-persona'
import {
  getInnFromUrl,
  getMockIsoDate,
  rejectMockNotFound,
  resolveMockResponse,
} from '@/app/mocks/mock-response'

interface ScheduledOperationMock {
  // Через сколько дней от сегодняшнего проходит операция
  day: number
  amount: number
  title: Record<AppLocale, string>
}

interface CashFlowMock {
  balance: number
  dailyInflow: number
  operations: ScheduledOperationMock[]
}

const HORIZON_DAYS = 30
const MOCK_CURRENCY = 'RUB'

/**
 * Исходные данные «бэкенда» для K1: остаток сегодня, ежедневные поступления и плановые операции.
 * У компаний без записи (новые персоны, банк) прогноза нет — `cash_forecast: null`.
 */
const cashFlowMock: Record<string, CashFlowMock> = {
  // Анна Смирнова — кассовый разрыв через 6 дней
  '770100000079': {
    balance: 184300,
    dailyInflow: 48000,
    operations: [
      { day: 2, amount: -230000, title: { ru: 'Зарплата сотрудникам', en: 'Staff payroll' } },
      { day: 4, amount: -150000, title: { ru: 'Аренда помещения', en: 'Premises rent' } },
      { day: 5, amount: -182300, title: { ru: 'Поставщики кофе и продуктов', en: 'Coffee and food suppliers' } },
      { day: 6, amount: -250000, title: { ru: 'Платёж по кредиту', en: 'Loan payment' } },
      { day: 10, amount: 268500, title: { ru: 'Оплата от корпоративных клиентов', en: 'Corporate client payments' } },
      { day: 15, amount: -160000, title: { ru: 'НДФЛ и страховые взносы', en: 'Payroll taxes and contributions' } },
      { day: 20, amount: -230000, title: { ru: 'Зарплата сотрудникам', en: 'Staff payroll' } },
    ],
  },
  // Павел Орлов — без разрыва
  '7701000019': {
    balance: 3920000,
    dailyInflow: 130000,
    operations: [
      { day: 7, amount: -1200000, title: { ru: 'Оплата поставщикам', en: 'Supplier payments' } },
      { day: 14, amount: -2750000, title: { ru: 'Платёж по кредиту и налоги', en: 'Loan payment and taxes' } },
      { day: 25, amount: -900000, title: { ru: 'Зарплата сотрудникам', en: 'Staff payroll' } },
    ],
  },
  // Елена Кравец — разрыв есть, но подходящего предложения K2 нет
  '7701000026': {
    balance: 1260000,
    dailyInflow: 20000,
    operations: [
      { day: 4, amount: -1100000, title: { ru: 'Оплата субподрядчикам', en: 'Subcontractor payments' } },
      { day: 7, amount: -400000, title: { ru: 'Закупка материалов', en: 'Materials purchase' } },
      { day: 20, amount: 5800000, title: { ru: 'Аванс по договору подряда', en: 'Construction contract advance' } },
    ],
  },
  // Игорь Белов — без разрыва
  '7701000033': {
    balance: 640000,
    dailyInflow: 90000,
    operations: [
      { day: 10, amount: -300000, title: { ru: 'Зарплата сотрудникам', en: 'Staff payroll' } },
      { day: 20, amount: -400000, title: { ru: 'Аренда и коммунальные платежи', en: 'Rent and utilities' } },
    ],
  },
  // Иван Иванов — кассовый разрыв через 8 дней
  '7701000040': {
    balance: 975400,
    dailyInflow: 30000,
    operations: [
      { day: 3, amount: -530000, title: { ru: 'Зарплата и страховые взносы', en: 'Payroll and contributions' } },
      { day: 5, amount: -480000, title: { ru: 'Оплата поставщику муки', en: 'Flour supplier payment' } },
      { day: 8, amount: -390000, title: { ru: 'Лизинг оборудования', en: 'Equipment leasing' } },
      { day: 12, amount: 720000, title: { ru: 'Оплата от сети магазинов', en: 'Retail chain payment' } },
    ],
  },
  // Олег Захаров — без разрыва
  '7701000065': {
    balance: 2310000,
    dailyInflow: 60000,
    operations: [
      { day: 10, amount: -1480000, title: { ru: 'Поставщики и логистика', en: 'Suppliers and logistics' } },
    ],
  },
}

/**
 * Имитирует расчёт K1 на бэкенде: остаток по дням, самая глубокая точка разрыва
 * и расходные операции до неё.
 */
function buildCashForecast(cashFlow: CashFlowMock, locale: AppLocale): CashForecastDto {
  const points: CashForecastPointDto[] = []
  let balance = cashFlow.balance

  for (let day = 0; day <= HORIZON_DAYS; day++) {
    if (day > 0) {
      balance += cashFlow.dailyInflow
    }

    balance += cashFlow.operations
      .filter((operation) => operation.day === day)
      .reduce((sum, operation) => sum + operation.amount, 0)

    points.push({ date: getMockIsoDate(day), balance })
  }

  const deepestIndex = points.reduce(
    (minIndex, point, index) => (point.balance < points[minIndex].balance ? index : minIndex),
    0,
  )
  const deepestPoint = points[deepestIndex]
  const hasCashGap = deepestPoint.balance < 0

  const operations: CashForecastOperationDto[] = hasCashGap
    ? cashFlow.operations
      .filter((operation) => operation.amount < 0 && operation.day <= deepestIndex)
      .map((operation) => ({
        id: `op-${operation.day}-${Math.abs(operation.amount)}`,
        date: getMockIsoDate(operation.day),
        title: operation.title[locale],
        amount: operation.amount,
      }))
    : []

  return {
    status: hasCashGap ? CashForecastStatusEnum.CashGap : CashForecastStatusEnum.Healthy,
    horizon_days: HORIZON_DAYS,
    currency: MOCK_CURRENCY,
    points,
    cash_gap: hasCashGap
      ? { date: deepestPoint.date, amount: Math.abs(deepestPoint.balance) }
      : null,
    operations,
  }
}

/**
 * Axios-адаптер для GET v1/companies/{inn}/insights.
 */
export function companyInsightsMockAdapter(
  config: InternalAxiosRequestConfig,
): Promise<AxiosResponse<ApiResponse<CompanyInsightsDto>>> {
  const locale: AppLocale = config.params?.lang === 'en' ? 'en' : 'ru'
  const inn = getInnFromUrl(config.url)

  if (!hasDemoPersonaMock(inn)) {
    return rejectMockNotFound(config)
  }

  const cashFlow = cashFlowMock[inn]

  return resolveMockResponse(config, {
    data: {
      inn,
      cash_forecast: cashFlow ? buildCashForecast(cashFlow, locale) : null,
    },
  })
}
