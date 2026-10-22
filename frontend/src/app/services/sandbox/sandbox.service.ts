import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { SandboxPersonaCreateDto } from '@/app/types/sandbox/sandbox-persona-create-dto'
import type { SandboxLoginDto } from '@/app/types/sandbox/sandbox-login-dto'
import type { SandboxPersonaDto } from '@/app/types/sandbox/sandbox-persona-dto'
import type { SandboxScenarioDto } from '@/app/types/sandbox/sandbox-scenario-dto'
import type { SandboxPersonaOptionsDto } from '@/app/types/sandbox/sandbox-persona-options-dto'
import type {
  SandboxClockAdvanceDto,
  SandboxClockDto,
  SandboxEventCreateDto,
  SandboxFaultCreateDto,
  SandboxFaultDto,
  SandboxWorkerDto,
} from '@/app/types/sandbox/sandbox-world-dto'

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

  // Сценарии по ролям: кем войти, что нажать и какой статус ждать на каждом шаге
  async fetchScenarios($fetch: AxiosInstance, locale: AppLocale) {
    return await $fetch.get<ApiResponse<SandboxScenarioDto[]>>(
      `${ROUTE_PREFIX_SANDBOX}/scenarios`,
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

  // ── Мир симулятора: часы, события реестров, отказы источников, воркер ─────────

  async fetchClock($fetch: AxiosInstance) {
    return await $fetch.get<ApiResponse<SandboxClockDto>>(`${ROUTE_PREFIX_SANDBOX}/clock`)
  },

  async advanceClock($fetch: AxiosInstance, payload: SandboxClockAdvanceDto) {
    return await $fetch.post<ApiResponse<SandboxClockDto>>(`${ROUTE_PREFIX_SANDBOX}/clock`, payload)
  },

  async createEvent($fetch: AxiosInstance, payload: SandboxEventCreateDto) {
    return await $fetch.post<ApiResponse<{ status: string }>>(`${ROUTE_PREFIX_SANDBOX}/events`, payload)
  },

  async fetchFaults($fetch: AxiosInstance) {
    return await $fetch.get<ApiResponse<SandboxFaultDto[]>>(`${ROUTE_PREFIX_SANDBOX}/faults`)
  },

  async createFault($fetch: AxiosInstance, payload: SandboxFaultCreateDto) {
    return await $fetch.post<ApiResponse<SandboxFaultDto>>(`${ROUTE_PREFIX_SANDBOX}/faults`, payload)
  },

  async deleteFault($fetch: AxiosInstance, faultId: string) {
    return await $fetch.delete(`${ROUTE_PREFIX_SANDBOX}/faults/${encodeURIComponent(faultId)}`)
  },

  async setWorkerPaused($fetch: AxiosInstance, isPaused: boolean) {
    return await $fetch.post<ApiResponse<SandboxWorkerDto>>(
      `${ROUTE_PREFIX_SANDBOX}/worker/${isPaused ? 'pause' : 'resume'}`,
    )
  },

  async reset($fetch: AxiosInstance) {
    return await $fetch.post<ApiResponse<{ status: string }>>(`${ROUTE_PREFIX_SANDBOX}/reset`)
  },
}
