import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { Nullable } from '@/app/types/nullable'

export interface SandboxPersonaPreviewCauseInterface {
  code: string
  text: string
  fields: string[]
}

export interface SandboxPersonaPreviewProductInterface {
  code: CreditProductCodeEnum
  name: string
  isAvailable: boolean
  // Порядок группы: доступен, с условиями, у специалиста, не подходит
  rank: number
  label: string
  maxAmount: Nullable<number>
  rate: Nullable<number>
  causes: SandboxPersonaPreviewCauseInterface[]
  isRecommended: boolean
}

export interface SandboxPersonaPreviewPersonInterface {
  badge: string
  fullName: string
  roleTitle: string
}

export interface SandboxPersonaPreviewInterface {
  companyName: string
  about: string
  pathMeans: string
  people: SandboxPersonaPreviewPersonInterface[]
  score: number
  riskClass: RiskClassEnum
  // Ответы, из-за которых балл снижен: подсвечиваются при наведении на класс риска
  scoreFields: string[]
  blockers: SandboxPersonaPreviewCauseInterface[]
  products: SandboxPersonaPreviewProductInterface[]
}
