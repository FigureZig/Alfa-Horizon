import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { SandboxPersonaCreateDto } from '@/app/types/sandbox/sandbox-persona-create-dto'
import type { SandboxPersonaDto } from '@/app/types/sandbox/sandbox-persona-dto'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'

const MOCK_RESPONSE_DELAY = 500

/**
 * Мок ответа GET v1/sandbox/personas?lang=<locale>.
 * Бэкенд отдаёт данные персон на языке из параметра `lang`.
 */
export const sandboxPersonasMock: Record<AppLocale, SandboxPersonaDto[]> = {
  ru: [
    {
      id: 's7',
      code: 'S7',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Анна Смирнова',
      organization: 'ИП Смирнова А. С. · кофейня',
      scenario: 'Банк заметил кассовый разрыв',
      permissions: 'ИП — все права, подписывает сама',
      profile: 'Поступления ≈ 1,5 млн ₽ в месяц, бизнесу 2 года',
      registries: 'Все источники отвечают',
      preview: 'Прогноз остатка, офер в один клик, проверку, оферту, подпись и выдачу',
      login_label: 'Войти как Анна',
    },
    {
      id: 's3',
      code: 'S3',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Павел Орлов',
      organization: 'ООО «Вектор-Трейд»',
      scenario: 'Хочу больше, чем позволяет нагрузка',
      permissions: 'Генеральный директор, единоличная подпись',
      profile: 'Выручка ≈ 12 млн ₽ в месяц, действующий кредит 8 млн ₽',
      registries: 'Все источники отвечают',
      preview: 'Расчёт долговой нагрузки, встречное предложение на меньшую сумму и вариант с залогом',
      login_label: 'Войти как Павел',
    },
    {
      id: 's2',
      code: 'S2',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Елена Кравец',
      organization: 'ООО «Мастер-Строй»',
      scenario: 'Крупная сделка: нужно решение участников',
      permissions: 'Директор, подписывает после одобрения участников',
      profile: 'Два участника по 50 %, запрошено 25 млн ₽ — крупная сделка',
      registries: 'ЕГРЮЛ: состав участников подтверждён',
      preview: 'Запрос решения участников, сбор согласий, контроль кворума и подпись',
      login_label: 'Войти как Елена',
    },
    {
      id: 's4',
      code: 'S4',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Игорь Белов',
      organization: 'ООО «Ромашка-Сервис»',
      scenario: 'Налоговая недоимка',
      permissions: 'Директор, все права',
      profile: 'Поступления ≈ 3 млн ₽ в месяц, бизнесу 5 лет',
      registries: 'ФНС: недоимка 340 тыс. ₽',
      preview: 'Стоп-фактор по заявке, план погашения недоимки и повторную проверку',
      login_label: 'Войти как Игорь',
    },
    {
      id: 'r8',
      code: 'R8',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Иван Иванов',
      organization: 'Три компании, три роли',
      scenario: 'Один человек — три компании',
      permissions: 'Директор в первой, бухгалтер во второй, участник в третьей',
      profile: 'Три организации с разными правами в одном профиле',
      registries: 'Все источники отвечают',
      preview: 'Переключение между компаниями и разные права подписи в каждой роли',
      login_label: 'Войти как Иван',
    },
    {
      id: 'r12',
      code: 'R12',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Олег Захаров',
      organization: 'ООО «Лента-Опт»',
      scenario: 'Смена директора во время подписи',
      permissions: 'Директор — полномочия прекращаются в процессе',
      profile: 'Поступления ≈ 6 млн ₽ в месяц, бизнесу 7 лет',
      registries: 'ЕГРЮЛ: внесена запись о новом директоре',
      preview: 'Отзыв полномочий, остановку подписи и переоформление на нового директора',
      login_label: 'Войти как Олег',
    },
    {
      id: 'n1',
      code: 'N1',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Анна Смирнова',
      organization: 'ИП Смирнова А. С. · кофейня',
      scenario: 'БКИ не отвечает во время проверки',
      permissions: 'ИП — все права, подписывает сама',
      profile: 'Поступления ≈ 1,5 млн ₽ в месяц, бизнесу 2 года',
      registries: 'БКИ недоступно, остальные источники отвечают',
      preview: 'Повторные запросы, ожидание ответа БКИ и уведомление о задержке решения',
      login_label: 'Войти как Анна',
    },
    {
      id: 'bank',
      code: 'Банк',
      kind: SandboxPersonaKindEnum.Bank,
      full_name: 'Мария Соколова',
      organization: 'Кредитный специалист',
      scenario: 'Очередь исключений и досье',
      permissions: 'Просмотр досье и решения по исключениям в пределах лимита',
      profile: 'Fino Банк, отдел кредитования малого бизнеса',
      registries: 'Доступ ко всем источникам по заявке',
      preview: 'Очередь исключений, досье клиента, комментарии и передачу риск-менеджеру',
      login_label: 'Войти как кредитный специалист',
    },
  ],
  en: [
    {
      id: 's7',
      code: 'S7',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Anna Smirnova',
      organization: 'Smirnova A. S., sole proprietor · coffee shop',
      scenario: 'The bank spotted a cash gap',
      permissions: 'Sole proprietor — full rights, signs herself',
      profile: 'Inflows ≈ ₽1.5M per month, business is 2 years old',
      registries: 'All sources respond',
      preview: 'Balance forecast, one-click offer, review, loan agreement, signing, and disbursement',
      login_label: 'Enter as Anna',
    },
    {
      id: 's3',
      code: 'S3',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Pavel Orlov',
      organization: 'Vector-Trade LLC',
      scenario: 'I want more than my debt load allows',
      permissions: 'CEO, sole signatory',
      profile: 'Revenue ≈ ₽12M per month, existing loan of ₽8M',
      registries: 'All sources respond',
      preview: 'Debt load calculation, a counteroffer for a smaller amount, and a secured option',
      login_label: 'Enter as Pavel',
    },
    {
      id: 's2',
      code: 'S2',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Elena Kravets',
      organization: 'Master-Stroy LLC',
      scenario: 'Major transaction: members must approve',
      permissions: 'Director, signs after members approve',
      profile: 'Two members with 50% each, ₽25M requested — a major transaction',
      registries: 'Company register: membership confirmed',
      preview: 'Requesting the members’ decision, collecting consents, quorum tracking, and signing',
      login_label: 'Enter as Elena',
    },
    {
      id: 's4',
      code: 'S4',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Igor Belov',
      organization: 'Romashka-Service LLC',
      scenario: 'Tax arrears',
      permissions: 'Director, full rights',
      profile: 'Inflows ≈ ₽3M per month, business is 5 years old',
      registries: 'Tax service: ₽340K in arrears',
      preview: 'A blocking stop factor, an arrears repayment plan, and a repeat check',
      login_label: 'Enter as Igor',
    },
    {
      id: 'r8',
      code: 'R8',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Ivan Ivanov',
      organization: 'Three companies, three roles',
      scenario: 'One person, three companies',
      permissions: 'Director in the first, accountant in the second, member in the third',
      profile: 'Three organizations with different rights in one profile',
      registries: 'All sources respond',
      preview: 'Switching between companies and different signing rights in each role',
      login_label: 'Enter as Ivan',
    },
    {
      id: 'r12',
      code: 'R12',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Oleg Zakharov',
      organization: 'Lenta-Opt LLC',
      scenario: 'Director changes during signing',
      permissions: 'Director — authority ends mid-process',
      profile: 'Inflows ≈ ₽6M per month, business is 7 years old',
      registries: 'Company register: new director recorded',
      preview: 'Revoked authority, halted signing, and re-issuing to the new director',
      login_label: 'Enter as Oleg',
    },
    {
      id: 'n1',
      code: 'N1',
      kind: SandboxPersonaKindEnum.Client,
      full_name: 'Anna Smirnova',
      organization: 'Smirnova A. S., sole proprietor · coffee shop',
      scenario: 'Credit bureau is down during the check',
      permissions: 'Sole proprietor — full rights, signs herself',
      profile: 'Inflows ≈ ₽1.5M per month, business is 2 years old',
      registries: 'Credit bureau unavailable, other sources respond',
      preview: 'Retries, waiting for the credit bureau, and a notice about the delayed decision',
      login_label: 'Enter as Anna',
    },
    {
      id: 'bank',
      code: 'Bank',
      kind: SandboxPersonaKindEnum.Bank,
      full_name: 'Maria Sokolova',
      organization: 'Loan officer',
      scenario: 'Exception queue and dossiers',
      permissions: 'View dossiers and decide on exceptions within limits',
      profile: 'Fino Bank, small business lending',
      registries: 'Access to all sources for an application',
      preview: 'Exception queue, client dossier, comments, and handover to a risk manager',
      login_label: 'Enter as loan officer',
    },
  ],
}

/**
 * Axios-адаптер, который вместо сетевого запроса возвращает мок с небольшой задержкой.
 */
export function sandboxPersonasMockAdapter(
  config: InternalAxiosRequestConfig,
): Promise<AxiosResponse<ApiResponse<SandboxPersonaDto[]>>> {
  const locale: AppLocale = config.params?.lang === 'en' ? 'en' : 'ru'

  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        data: { data: sandboxPersonasMock[locale] },
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      })
    }, MOCK_RESPONSE_DELAY)
  })
}

/**
 * Axios-адаптер для POST v1/sandbox/personas: добавляет персону в мок-список,
 * чтобы она появилась на странице /sandbox после возврата.
 */
export function sandboxPersonaCreateMockAdapter(
  config: InternalAxiosRequestConfig,
): Promise<AxiosResponse<ApiResponse<SandboxPersonaDto>>> {
  const payload: SandboxPersonaCreateDto = JSON.parse(config.data)

  const persona: SandboxPersonaDto = {
    id: `custom-${Date.now()}`,
    ...payload,
  }

  return new Promise((resolve) => {
    setTimeout(() => {
      sandboxPersonasMock.ru.push(persona)
      sandboxPersonasMock.en.push(persona)

      resolve({
        data: { data: persona },
        status: 201,
        statusText: 'Created',
        headers: {},
        config,
      })
    }, MOCK_RESPONSE_DELAY)
  })
}
