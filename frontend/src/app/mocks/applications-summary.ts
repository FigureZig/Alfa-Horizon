import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { Nullable } from '@/app/types/nullable'
import type { ApplicationsSummaryDto } from '@/app/types/application/applications-summary-dto'
import { ApplicationStatusEnum } from '@/app/types/application/application-status-enum'
import { TaskTypeEnum } from '@/app/types/application/task-type-enum'
import { hasDemoPersonaMock } from '@/app/mocks/demo-persona'
import {
  getInnFromUrl,
  getMockIsoDate,
  getMockIsoDateTime,
  rejectMockNotFound,
  rejectMockServiceUnavailable,
  resolveMockResponse,
} from '@/app/mocks/mock-response'

interface ApplicationMock {
  id: string
  productName: Record<AppLocale, string>
  amount: number
  status: ApplicationStatusEnum
  // Сколько дней назад заявка менялась
  updatedDaysAgo: number
}

interface TaskMock {
  id: string
  type: TaskTypeEnum
  title: Record<AppLocale, string>
  // Через сколько дней срок; null — без срока
  dueInDays: Nullable<number>
  applicationId: Nullable<string>
}

interface ApplicationsSummaryMock {
  applications: ApplicationMock[]
  tasks: TaskMock[]
}

const MOCK_CURRENCY = 'RUB'

// Для этих ИНН сервис заявок «недоступен» — проверка независимости виджетов
const UNAVAILABLE_INNS = ['7701000026']

/**
 * Сводка заявок и задач по ИНН. Компании без записи — без заявок и задач.
 */
const applicationsSummaryMock: Record<string, ApplicationsSummaryMock> = {
  // Павел Орлов — одобренная заявка, задач нет
  '7701000019': {
    applications: [
      {
        id: 'app-7701000019-1',
        productName: { ru: 'Кредит под залог недвижимости', en: 'Real estate secured loan' },
        amount: 15000000,
        status: ApplicationStatusEnum.Approved,
        updatedDaysAgo: 3,
      },
    ],
    tasks: [],
  },
  // Игорь Белов — заявок нет, банк запросил документ
  '7701000033': {
    applications: [],
    tasks: [
      {
        id: 'task-7701000033-1',
        type: TaskTypeEnum.DocumentRequest,
        title: {
          ru: 'Загрузить справку об отсутствии налоговой задолженности',
          en: 'Upload a certificate of no tax arrears',
        },
        dueInDays: 5,
        applicationId: null,
      },
    ],
  },
  // Иван Иванов — заявка ждёт подписи
  '7701000040': {
    applications: [
      {
        id: 'app-7701000040-1',
        productName: { ru: 'Возобновляемая кредитная линия', en: 'Revolving credit line' },
        amount: 500000,
        status: ApplicationStatusEnum.ActionRequired,
        updatedDaysAgo: 0,
      },
    ],
    tasks: [
      {
        id: 'task-7701000040-1',
        type: TaskTypeEnum.Signature,
        title: { ru: 'Подписать кредитный договор', en: 'Sign the loan agreement' },
        dueInDays: 2,
        applicationId: 'app-7701000040-1',
      },
    ],
  },
  // Олег Захаров — несколько заявок и задач
  '7701000065': {
    applications: [
      {
        id: 'app-7701000065-1',
        productName: { ru: 'Кредит на пополнение оборотных средств', en: 'Working capital loan' },
        amount: 3000000,
        status: ApplicationStatusEnum.InReview,
        updatedDaysAgo: 1,
      },
      {
        id: 'app-7701000065-2',
        productName: { ru: 'Овердрафт', en: 'Overdraft' },
        amount: 800000,
        status: ApplicationStatusEnum.Submitted,
        updatedDaysAgo: 2,
      },
    ],
    tasks: [
      {
        id: 'task-7701000065-1',
        type: TaskTypeEnum.Signature,
        title: { ru: 'Подписать согласие на запрос в БКИ', en: 'Sign the credit bureau consent' },
        dueInDays: 1,
        applicationId: 'app-7701000065-1',
      },
      {
        id: 'task-7701000065-2',
        type: TaskTypeEnum.DocumentRequest,
        title: { ru: 'Обновить решение о назначении директора', en: 'Update the director appointment decision' },
        dueInDays: null,
        applicationId: 'app-7701000065-1',
      },
    ],
  },
}

/**
 * Axios-адаптер для GET v1/companies/{inn}/applications/summary (предлагаемый контракт).
 */
export function applicationsSummaryMockAdapter(
  config: InternalAxiosRequestConfig,
): Promise<AxiosResponse<ApiResponse<ApplicationsSummaryDto>>> {
  const locale: AppLocale = config.params?.lang === 'en' ? 'en' : 'ru'
  const inn = getInnFromUrl(config.url)

  if (!hasDemoPersonaMock(inn)) {
    return rejectMockNotFound(config)
  }

  if (UNAVAILABLE_INNS.includes(inn)) {
    return rejectMockServiceUnavailable(config)
  }

  const summary = applicationsSummaryMock[inn] ?? { applications: [], tasks: [] }

  return resolveMockResponse(config, {
    data: {
      applications: summary.applications.map((application) => ({
        id: application.id,
        product_name: application.productName[locale],
        amount: application.amount,
        currency: MOCK_CURRENCY,
        status: application.status,
        updated_at: getMockIsoDateTime(-application.updatedDaysAgo, 11, 30),
      })),
      tasks: summary.tasks.map((task) => ({
        id: task.id,
        type: task.type,
        title: task.title[locale],
        due_date: task.dueInDays === null ? null : getMockIsoDate(task.dueInDays),
        application_id: task.applicationId,
      })),
    },
  })
}
