import type { AxiosInstance } from 'axios'
import type { ApiResponse } from '@/app/types/api-response'

const ROUTE_PREFIX_AUTH = 'v1/auth'

export const authService = {
  async logout($fetch: AxiosInstance) {
    return await $fetch.post<ApiResponse<{ status: string }>>(
      `${ROUTE_PREFIX_AUTH}/logout`,
      null,
    )
  },
}
