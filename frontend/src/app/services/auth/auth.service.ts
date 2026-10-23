import type { AxiosInstance } from 'axios'
import type { ApiResponse } from '@/app/types/api-response'
import type { SandboxLoginDto } from '@/app/types/sandbox/sandbox-login-dto'
import type { MeDto } from '@/app/types/company/company-access-dto'

const ROUTE_PREFIX_AUTH = 'v1/auth'

export const authService = {
  // Вход по ID пользователя, ИНН человека или ИНН компании; ответ тот же, что у входа карточкой
  async login($fetch: AxiosInstance, login: string, lang: string) {
    return await $fetch.post<ApiResponse<SandboxLoginDto>>(
      `${ROUTE_PREFIX_AUTH}/login`,
      { login },
      {
        params: { lang },
      },
    )
  },

  // Кто я и что мне можно в каждой моей компании
  async fetchMe($fetch: AxiosInstance) {
    return await $fetch.get<ApiResponse<MeDto>>('v1/me')
  },

  // Сделать компанию активной: от неё бэкенд считает входящие задачи
  async switchCompany($fetch: AxiosInstance, inn: string) {
    return await $fetch.put<ApiResponse<{ active_company_inn: string }>>('v1/me/company', { inn })
  },

  async logout($fetch: AxiosInstance) {
    return await $fetch.post<ApiResponse<{ status: string }>>(
      `${ROUTE_PREFIX_AUTH}/logout`,
      null,
    )
  },
}
