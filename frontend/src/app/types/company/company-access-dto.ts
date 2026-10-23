import type { Nullable } from '@/app/types/nullable'

// Права человека в компании: считает бэкенд, фронт их не вычисляет
export interface CompanyAccessRightsDto {
  view: boolean
  prepare: boolean
  sign: boolean
  approve: boolean
}

export interface CompanyAccessRoleDto {
  role: string
  // Доля участника ООО, %
  share?: number
}

/**
 * Компания пользователя: элемент `companies` в ответе входа и в GET v1/me.
 * Участник ООО без доступа в интернет-банк видит только голосование: `can.view = false`, `can.approve = true`.
 */
export interface CompanyAccessDto {
  inn: string
  name: string
  short_name: string
  can: CompanyAccessRightsDto
  roles: CompanyAccessRoleDto[]
}

/** Ответ GET v1/me. */
export interface MeDto {
  persona: { person_inn: Nullable<string> }
  companies: CompanyAccessDto[]
  active_company_inn: Nullable<string>
}
