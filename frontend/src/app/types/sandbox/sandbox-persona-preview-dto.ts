import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { Nullable } from '@/app/types/nullable'

// Почему продукт недоступен или компании стоп: `fields` — ответы конструктора, от которых зависит причина
export interface SandboxPersonaPreviewCauseDto {
  code: string
  kind: Nullable<string>
  text: string
  fields: string[]
}

export interface SandboxPersonaPreviewProductDto {
  product: CreditProductCodeEnum
  name: string
  available: boolean
  // PREAPPROVED · CONDITIONAL · REVIEW · UNAVAILABLE
  label: string
  max_amount: Nullable<number>
  rate: Nullable<number>
  payment: Nullable<number>
  why: SandboxPersonaPreviewCauseDto[]
  recommended: boolean
}

export interface SandboxPersonaPreviewFactorDto {
  factor: string
  title: string
  effect: string
  points: number
  fields: string[]
}

export interface SandboxPersonaPreviewPersonDto {
  badge: string
  full_name: string
  role_title: string
}

/**
 * Ответ POST v1/sandbox/personas/preview: что банк скажет о такой компании до создания.
 * Те же факты, скоринг и подбор, что у созданной компании, только без сохранения.
 */
export interface SandboxPersonaPreviewDto {
  form: string
  company: { name: string, about: string }
  path: { structure: Nullable<string>, sign_mode: string, means: string }
  people: SandboxPersonaPreviewPersonDto[]
  score: { score: number, class: RiskClassEnum, factors: SandboxPersonaPreviewFactorDto[] }
  blockers: SandboxPersonaPreviewCauseDto[]
  products: SandboxPersonaPreviewProductDto[]
  recommended: Nullable<string>
}
