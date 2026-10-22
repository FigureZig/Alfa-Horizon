import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { Nullable } from '@/app/types/nullable'

export interface SandboxPersonaFormOptionDto {
  id: LegalFormEnum
  title: string
}

export interface SandboxPersonaFlagGroupDto {
  id: string
  title: string
}

export interface SandboxPersonaFlagDto {
  id: string
  group: string
  title: string
  effect: string
  forms: LegalFormEnum[]
}

export interface SandboxPersonaParamDto {
  id: string
  type: string
  default: Nullable<number | string>
  description: string
  ge?: number
  le?: number
  gt?: number
}

/**
 * Ответ GET v1/sandbox/persona-options — что можно задать своей компании:
 * формы, параметры с границами и значениями по умолчанию, флаги, которые меняют решение банка.
 */
export interface SandboxPersonaOptionsDto {
  forms: SandboxPersonaFormOptionDto[]
  groups: SandboxPersonaFlagGroupDto[]
  flags: SandboxPersonaFlagDto[]
  params: SandboxPersonaParamDto[]
}
