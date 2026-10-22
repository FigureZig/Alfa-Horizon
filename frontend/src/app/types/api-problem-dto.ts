import type { ApiErrorCodeEnum } from '@/app/types/api-error-code-enum'

/**
 * Ошибка API в формате RFC 9457 (application/problem+json).
 * Ветвиться — по `code`; `detail` — текст для людей. Остальные поля зависят от кода
 * (например, `suggested_inn` у INN_INVALID, `errors` у VALIDATION_ERROR).
 */
export interface ApiProblemDto {
  type: string
  title: string
  status: number
  detail: string
  code: ApiErrorCodeEnum | string
  [extra: string]: unknown
}
