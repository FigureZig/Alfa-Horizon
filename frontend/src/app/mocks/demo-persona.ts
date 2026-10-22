import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { DemoPersonaDto } from '@/app/types/demo-persona/demo-persona-dto'
import type { SandboxPersonaDto } from '@/app/types/sandbox/sandbox-persona-dto'
import {
  getInnFromUrl,
  rejectMockNotFound,
  resolveMockResponse,
} from '@/app/mocks/mock-response'

/**
 * Мок ответа GET v1/demo-personas/:inn?lang=<locale>.
 * Персоны ищутся по ИНН компании.
 */
export const demoPersonasMock: Record<AppLocale, DemoPersonaDto[]> = {
  ru: [
    { inn: '770100000079', first_name: 'Анна', last_name: 'Смирнова', initials: 'АС', organization_name: 'ИП Смирнова А. С.' },
    { inn: '7701000019', first_name: 'Павел', last_name: 'Орлов', initials: 'ПО', organization_name: 'ООО «Вектор-Трейд»' },
    { inn: '7701000026', first_name: 'Елена', last_name: 'Кравец', initials: 'ЕК', organization_name: 'ООО «Мастер-Строй»' },
    { inn: '7701000033', first_name: 'Игорь', last_name: 'Белов', initials: 'ИБ', organization_name: 'ООО «Ромашка-Сервис»' },
    { inn: '7701000040', first_name: 'Иван', last_name: 'Иванов', initials: 'ИИ', organization_name: 'ООО «Северный Хлеб»' },
    { inn: '7701000065', first_name: 'Олег', last_name: 'Захаров', initials: 'ОЗ', organization_name: 'ООО «Лента-Опт»' },
    { inn: '7701000097', first_name: 'Мария', last_name: 'Соколова', initials: 'МС', organization_name: 'Fino Банк' },
  ],
  en: [
    { inn: '770100000079', first_name: 'Anna', last_name: 'Smirnova', initials: 'AS', organization_name: 'Smirnova A. S., sole proprietor' },
    { inn: '7701000019', first_name: 'Pavel', last_name: 'Orlov', initials: 'PO', organization_name: 'Vector-Trade LLC' },
    { inn: '7701000026', first_name: 'Elena', last_name: 'Kravets', initials: 'EK', organization_name: 'Master-Stroy LLC' },
    { inn: '7701000033', first_name: 'Igor', last_name: 'Belov', initials: 'IB', organization_name: 'Romashka-Service LLC' },
    { inn: '7701000040', first_name: 'Ivan', last_name: 'Ivanov', initials: 'II', organization_name: 'Severny Khleb LLC' },
    { inn: '7701000065', first_name: 'Oleg', last_name: 'Zakharov', initials: 'OZ', organization_name: 'Lenta-Opt LLC' },
    { inn: '7701000097', first_name: 'Maria', last_name: 'Sokolova', initials: 'MS', organization_name: 'Fino Bank' },
  ],
}

export function hasDemoPersonaMock(inn: string): boolean {
  return demoPersonasMock.ru.some((persona) => persona.inn === inn)
}

/**
 * Регистрирует персону, созданную в конструкторе, чтобы в её кабинет можно было войти по ИНН.
 */
export function addDemoPersonaMock(persona: SandboxPersonaDto) {
  if (hasDemoPersonaMock(persona.inn)) return

  const [firstName = '', ...lastNameParts] = persona.full_name.split(' ').filter(Boolean)
  const lastName = lastNameParts.join(' ')

  const demoPersona: DemoPersonaDto = {
    inn: persona.inn,
    first_name: firstName,
    last_name: lastName,
    initials: `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase(),
    organization_name: persona.organization,
  }

  demoPersonasMock.ru.push(demoPersona)
  demoPersonasMock.en.push(demoPersona)
}

/**
 * Axios-адаптер для GET v1/demo-personas/:inn. Для неизвестного ИНН отвечает 404.
 */
export function demoPersonaMockAdapter(
  config: InternalAxiosRequestConfig,
): Promise<AxiosResponse<ApiResponse<DemoPersonaDto>>> {
  const locale: AppLocale = config.params?.lang === 'en' ? 'en' : 'ru'
  const inn = getInnFromUrl(config.url)
  const persona = demoPersonasMock[locale].find((item) => item.inn === inn)

  if (!persona) {
    return rejectMockNotFound(config)
  }

  return resolveMockResponse(config, { data: persona })
}
