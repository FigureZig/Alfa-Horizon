import type { AxiosInstance } from 'axios'
import type { AppLocale } from '@/app/i18n'
import type { ApiResponse } from '@/app/types/api-response'
import type { ApplicationCreateDto, ApplicationInfoAnswerDto } from '@/app/types/application/application-create-dto'
import type { ApplicationDto } from '@/app/types/application/application-dto'
import type { ApplicationEventDto } from '@/app/types/application/application-event-dto'
import type { ApplicationExplanationDto } from '@/app/types/application/application-explanation-dto'
import type { ApplicationVoteEnum } from '@/app/types/application/application-vote-enum'
import type { ApplicationsSummaryDto } from '@/app/types/application/applications-summary-dto'

const ROUTE_PREFIX_COMPANIES = 'v1/companies'
const ROUTE_PREFIX_APPLICATIONS = 'v1/applications'

function applicationRoute(applicationId: string): string {
  return `${ROUTE_PREFIX_APPLICATIONS}/${encodeURIComponent(applicationId)}`
}

export const applicationsService = {
  // Сводка для главной: заявки и задачи компании
  async fetchSummary($fetch: AxiosInstance, inn: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<ApplicationsSummaryDto>>(
      `${ROUTE_PREFIX_COMPANIES}/${encodeURIComponent(inn)}/applications/summary`,
      {
        params: { lang: locale },
      },
    )
  },

  async fetchApplications($fetch: AxiosInstance, inn: string) {
    return await $fetch.get<ApiResponse<ApplicationDto[]>>(
      ROUTE_PREFIX_APPLICATIONS,
      {
        params: { company_inn: inn },
      },
    )
  },

  async fetchApplication($fetch: AxiosInstance, applicationId: string) {
    return await $fetch.get<ApiResponse<ApplicationDto>>(applicationRoute(applicationId))
  },

  async fetchEvents($fetch: AxiosInstance, applicationId: string) {
    return await $fetch.get<ApiResponse<ApplicationEventDto[]>>(`${applicationRoute(applicationId)}/events`)
  },

  async fetchExplanation($fetch: AxiosInstance, applicationId: string, locale: AppLocale) {
    return await $fetch.get<ApiResponse<ApplicationExplanationDto>>(
      `${applicationRoute(applicationId)}/explain`,
      {
        params: { lang: locale },
      },
    )
  },

  // Черновик заявки; подача — отдельной командой submit
  async createApplication($fetch: AxiosInstance, payload: ApplicationCreateDto) {
    return await $fetch.post<ApiResponse<ApplicationDto>>(ROUTE_PREFIX_APPLICATIONS, payload)
  },

  // Idempotency-Key: повтор с тем же ключом не создаёт дублей
  async submitApplication($fetch: AxiosInstance, applicationId: string, idempotencyKey: string) {
    return await $fetch.post<ApiResponse<ApplicationDto>>(
      `${applicationRoute(applicationId)}/submit`,
      null,
      {
        headers: { 'Idempotency-Key': idempotencyKey },
      },
    )
  },

  async withdrawApplication($fetch: AxiosInstance, applicationId: string) {
    return await $fetch.post<ApiResponse<ApplicationDto>>(`${applicationRoute(applicationId)}/withdraw`)
  },

  // variant: 0 — основной вариант оферты, 1… — альтернативы из offers
  async acceptOffer($fetch: AxiosInstance, applicationId: string, variant: number) {
    return await $fetch.post<ApiResponse<ApplicationDto>>(
      `${applicationRoute(applicationId)}/offer/accept`,
      { variant },
    )
  },

  async declineOffer($fetch: AxiosInstance, applicationId: string) {
    return await $fetch.post<ApiResponse<ApplicationDto>>(`${applicationRoute(applicationId)}/offer/decline`)
  },

  async signApplication($fetch: AxiosInstance, applicationId: string) {
    return await $fetch.post<ApiResponse<ApplicationDto>>(`${applicationRoute(applicationId)}/signatures`)
  },

  async answerInfoRequest($fetch: AxiosInstance, applicationId: string, payload: ApplicationInfoAnswerDto) {
    return await $fetch.post<ApiResponse<ApplicationDto>>(
      `${applicationRoute(applicationId)}/info-requests/answer`,
      payload,
    )
  },

  async voteForLargeDeal($fetch: AxiosInstance, applicationId: string, vote: ApplicationVoteEnum) {
    return await $fetch.post<ApiResponse<ApplicationDto>>(
      `${applicationRoute(applicationId)}/approvals/vote`,
      { vote },
    )
  },
}
