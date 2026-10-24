import { readonly, ref } from 'vue'
import axios, { HttpStatusCode, isAxiosError } from 'axios'
import type { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { ApiErrorCodeEnum } from '@/app/types/api-error-code-enum'
import type { ApiProblemDto } from '@/app/types/api-problem-dto'
import type { Nullable } from '@/app/types/nullable'

const TOKEN_STORAGE_KEY = 'fino-token'
const REQUEST_TIMEOUT = 15000

// Пока банк собирает данные компании, API отвечает 409 COMPANY_NOT_LOADED — повторяем с паузой
const NOT_LOADED_RETRY_LIMIT = 5
const NOT_LOADED_RETRY_DELAY = 1500

const SESSION_ERROR_CODES: string[] = [ApiErrorCodeEnum.TokenInvalid, ApiErrorCodeEnum.UserUnknown]

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  notLoadedRetryCount?: number
  isSessionRetried?: boolean
}

// ── Токен демо-сессии ──────────────────────────────────────────────────────────
// Хранится между перезагрузками; без токена симулятор открывает кабинет пользователем компании по ИНН.

function readStoredToken(): Nullable<string> {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

const sessionToken = ref<Nullable<string>>(readStoredToken())

// Токен — это человек, под которым вошли: кабинет следит за ним и при смене человека перечитывает себя
export const currentSessionToken = readonly(sessionToken)

export function getSessionToken(): Nullable<string> {
  return sessionToken.value
}

export function setSessionToken(token: string) {
  sessionToken.value = token

  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } catch {
    // Хранилище недоступно (приватный режим) — токен живёт до перезагрузки
  }
}

export function clearSessionToken() {
  sessionToken.value = null

  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch {
    // Хранилище недоступно — очищать нечего
  }
}

// ── Ошибки API (RFC 9457) ──────────────────────────────────────────────────────

export function getApiProblem(err: unknown): Nullable<ApiProblemDto> {
  if (!isAxiosError(err)) return null

  const data: unknown = err.response?.data

  return data && typeof data === 'object' && 'code' in data ? (data as ApiProblemDto) : null
}

export function getApiErrorCode(err: unknown): Nullable<string> {
  return getApiProblem(err)?.code ?? null
}

export function isNotFoundError(err: unknown): boolean {
  return isAxiosError(err) && err.response?.status === HttpStatusCode.NotFound
}

// ── Клиент ─────────────────────────────────────────────────────────────────────

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    Accept: 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  if (sessionToken.value) {
    config.headers.Authorization = `Bearer ${sessionToken.value}`
  }

  return config
})

apiClient.interceptors.response.use(undefined, async (err: AxiosError) => {
  const code = getApiErrorCode(err)
  const config = err.config as RetryableRequestConfig | undefined

  if (!config) return Promise.reject(err)

  const retryCount = config.notLoadedRetryCount ?? 0

  if (code === ApiErrorCodeEnum.CompanyNotLoaded && retryCount < NOT_LOADED_RETRY_LIMIT) {
    config.notLoadedRetryCount = retryCount + 1
    await wait(NOT_LOADED_RETRY_DELAY)

    return apiClient.request(config)
  }

  // Токен истёк или пользователя больше нет — забываем его и повторяем запрос без токена
  if (code && SESSION_ERROR_CODES.includes(code) && !config.isSessionRetried) {
    clearSessionToken()
    config.isSessionRetried = true
    delete config.headers.Authorization

    return apiClient.request(config)
  }

  return Promise.reject(err)
})

/**
 * Настроенный клиент API — один на приложение: токен сессии, повтор при сборе данных, сброс устаревшей сессии.
 */
export function useApiFetch() {
  return apiClient
}
