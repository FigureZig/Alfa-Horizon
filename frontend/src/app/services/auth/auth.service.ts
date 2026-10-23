import type { AxiosInstance } from 'axios'
import type { ApiResponse } from '@/app/types/api-response'
import type { MeDto } from '@/app/types/company/company-access-dto'

const ROUTE_PREFIX_AUTH = 'v1/auth'

export const authService = {
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
