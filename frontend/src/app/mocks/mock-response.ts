import { AxiosError, HttpStatusCode } from 'axios'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'

const MOCK_RESPONSE_DELAY = 500

/**
 * Имитирует успешный HTTP-ответ с небольшой задержкой.
 */
export function resolveMockResponse<T>(
  config: InternalAxiosRequestConfig,
  data: T,
): Promise<AxiosResponse<T>> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        data,
        status: HttpStatusCode.Ok,
        statusText: 'OK',
        headers: {},
        config,
      })
    }, MOCK_RESPONSE_DELAY)
  })
}

function rejectMockResponse(
  config: InternalAxiosRequestConfig,
  status: HttpStatusCode,
  statusText: string,
  code: string,
): Promise<never> {
  const response: AxiosResponse<{ detail: string }> = {
    data: { detail: statusText },
    status,
    statusText,
    headers: {},
    config,
  }

  return new Promise((_, reject) => {
    setTimeout(() => {
      reject(new AxiosError(
        `Request failed with status code ${status}`,
        code,
        config,
        null,
        response,
      ))
    }, MOCK_RESPONSE_DELAY)
  })
}

/**
 * Имитирует ответ 404 так же, как его вернул бы Axios для реального запроса.
 */
export function rejectMockNotFound(config: InternalAxiosRequestConfig): Promise<never> {
  return rejectMockResponse(config, HttpStatusCode.NotFound, 'Not Found', AxiosError.ERR_BAD_REQUEST)
}

/**
 * Имитирует недоступность сервиса (503) — для проверки ошибок отдельных виджетов.
 */
export function rejectMockServiceUnavailable(config: InternalAxiosRequestConfig): Promise<never> {
  return rejectMockResponse(
    config,
    HttpStatusCode.ServiceUnavailable,
    'Service Unavailable',
    AxiosError.ERR_BAD_RESPONSE,
  )
}

/**
 * Достаёт ИНН из адреса вида `v1/demo-personas/<inn>/...` или `v1/companies/<inn>/...`.
 */
export function getInnFromUrl(url = ''): string {
  const match = url.match(/(?:demo-personas|companies)\/([^/?]+)/)

  return match ? decodeURIComponent(match[1]) : ''
}

/**
 * Дата через `daysAhead` дней от сегодняшней в формате YYYY-MM-DD — моки не устаревают со временем.
 */
export function getMockIsoDate(daysAhead: number): string {
  const date = new Date()
  date.setDate(date.getDate() + daysAhead)

  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${date.getFullYear()}-${month}-${day}`
}

/**
 * Момент времени `daysAhead` дней от сегодня в заданные часы и минуты, в ISO 8601.
 */
export function getMockIsoDateTime(daysAhead: number, hours: number, minutes: number): string {
  const date = new Date()
  date.setDate(date.getDate() + daysAhead)
  date.setHours(hours, minutes, 0, 0)

  return date.toISOString()
}
