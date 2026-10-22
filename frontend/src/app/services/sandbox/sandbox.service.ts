import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { SandboxPersonaCreateDto } from '@/app/types/sandbox/sandbox-persona-create-dto'
import type { SandboxLoginDto } from '@/app/types/sandbox/sandbox-login-dto'
import type { SandboxPersonaDto } from '@/app/types/sandbox/sandbox-persona-dto'
import type { SandboxPersonaOptionsDto } from '@/app/types/sandbox/sandbox-persona-options-dto'

const ROUTE_PREFIX_SANDBOX = 'v1/sandbox'

export const sandboxService = {
  async fetchPersonas($fetch: AxiosInstance, locale: AppLocale) {
    return await $fetch.get<ApiResponse<SandboxPersonaDto[]>>(
      `${ROUTE_PREFIX_SANDBOX}/personas`,
      {
        params: { lang: locale },
      },
    )
  },

  // Что можно задать своей компании: формы, параметры с границами, флаги
  async fetchPersonaOptions($fetch: AxiosInstance, locale: AppLocale) {
    return await $fetch.get<ApiResponse<SandboxPersonaOptionsDto>>(
      `${ROUTE_PREFIX_SANDBOX}/persona-options`,
      {
        params: { lang: locale },
      },
    )
  },

  // Вход персоной: банк начинает собирать данные её компаний, в ответе — JWT для заголовка Authorization
  async loginAsPersona($fetch: AxiosInstance, personaId: string, locale: AppLocale) {
    return await $fetch.post<ApiResponse<SandboxLoginDto>>(
      `${ROUTE_PREFIX_SANDBOX}/personas/${encodeURIComponent(personaId)}/login`,
      null,
      {
        params: { lang: locale },
      },
    )
  },

  async createPersona($fetch: AxiosInstance, payload: SandboxPersonaCreateDto) {
    return await $fetch.post<ApiResponse<SandboxPersonaDto>>(
      `${ROUTE_PREFIX_SANDBOX}/personas`,
      payload,
    )
  },
}
