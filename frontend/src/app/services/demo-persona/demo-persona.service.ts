import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { DemoPersonaDto } from '@/app/types/demo-persona/demo-persona-dto'

const ROUTE_PREFIX_DEMO_PERSONAS = 'v1/demo-personas'

export const demoPersonaService = {
  async fetchDemoPersona($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<DemoPersonaDto>>(
      `${ROUTE_PREFIX_DEMO_PERSONAS}/${encodeURIComponent(inn)}`,
      {
        params: { lang: locale },
      },
    )
  },
}
