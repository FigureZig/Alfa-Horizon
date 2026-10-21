import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { SandboxPersonaCreateDto } from '@/app/types/sandbox/sandbox-persona-create-dto'
import type { SandboxPersonaDto } from '@/app/types/sandbox/sandbox-persona-dto'
import {
  sandboxPersonaCreateMockAdapter,
  sandboxPersonasMockAdapter,
} from '@/app/mocks/sandbox'

const ROUTE_PREFIX_SANDBOX = 'v1/sandbox'

export const sandboxService = {
  async fetchPersonas($fetch: AxiosInstance, locale: AppLocale) {
    return await $fetch.get<ApiResponse<SandboxPersonaDto[]>>(
      `${ROUTE_PREFIX_SANDBOX}/personas`,
      {
        params: { lang: locale },
        // Пока нет API, ответ отдаёт мок. Удалите adapter, чтобы запрос ушёл на бэкенд.
        adapter: sandboxPersonasMockAdapter,
      },
    )
  },

  async createPersona($fetch: AxiosInstance, payload: SandboxPersonaCreateDto) {
    return await $fetch.post<ApiResponse<SandboxPersonaDto>>(
      `${ROUTE_PREFIX_SANDBOX}/personas`,
      payload,
      {
        // Пока нет API, ответ отдаёт мок. Удалите adapter, чтобы запрос ушёл на бэкенд.
        adapter: sandboxPersonaCreateMockAdapter,
      },
    )
  },
}
