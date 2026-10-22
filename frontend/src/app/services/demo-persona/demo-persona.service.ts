import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { DemoPersonaDto } from '@/app/types/demo-persona/demo-persona-dto'
import { demoPersonaMockAdapter } from '@/app/mocks/demo-persona'

const ROUTE_PREFIX_DEMO_PERSONAS = 'v1/demo-personas'

export const demoPersonaService = {
  async fetchDemoPersona($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<DemoPersonaDto>>(
      `${ROUTE_PREFIX_DEMO_PERSONAS}/${encodeURIComponent(inn)}`,
      {
        params: { lang: locale },
        // Пока нет API, ответ отдаёт мок. Удалите adapter, чтобы запрос ушёл на бэкенд.
        adapter: demoPersonaMockAdapter,
      },
    )
  },
}
