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

// Отрасль из каталога: ОКВЭД, сезонность и канал оплаты по умолчанию
export interface SandboxPersonaIndustryDto {
  id: string
  title: string
  okved: string
  okved_name: string
  seasonality: string
  channel: string
}

// Устройство компании и люди: `means` — что из этого следует для подписи и крупной сделки, с нормой закона
export interface SandboxPersonaStructureDto {
  id: string
  title: string
  means: string
  forms: LegalFormEnum[]
}

export interface SandboxPersonaPeopleDto {
  id: string
  title: string
  means: string
  forms: LegalFormEnum[]
}

export interface SandboxPersonaChoiceDto {
  id: string
  title: string
}

export interface SandboxPersonaChoicesDto {
  seasonality: SandboxPersonaChoiceDto[]
  stability: SandboxPersonaChoiceDto[]
  trend: SandboxPersonaChoiceDto[]
  channel: SandboxPersonaChoiceDto[]
  loans: SandboxPersonaChoiceDto[]
  delays: SandboxPersonaChoiceDto[]
}

/**
 * Ответ GET v1/sandbox/persona-options — вопросы конструктора своей компании:
 * формы, отрасли, устройство и люди, простые ответы про деньги, особенности и точные цифры.
 */
export interface SandboxPersonaOptionsDto {
  forms: SandboxPersonaFormOptionDto[]
  industries: SandboxPersonaIndustryDto[]
  structures: SandboxPersonaStructureDto[]
  people: SandboxPersonaPeopleDto[]
  choices: SandboxPersonaChoicesDto
  groups: SandboxPersonaFlagGroupDto[]
  flags: SandboxPersonaFlagDto[]
  params: SandboxPersonaParamDto[]
}
