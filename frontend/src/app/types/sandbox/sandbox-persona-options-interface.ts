import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { Nullable } from '@/app/types/nullable'

export interface SandboxPersonaFormOptionInterface {
  id: LegalFormEnum
  title: string
}

export interface SandboxPersonaFlagGroupInterface {
  id: string
  title: string
}

export interface SandboxPersonaFlagInterface {
  id: string
  group: string
  title: string
  effect: string
  forms: LegalFormEnum[]
}

export interface SandboxPersonaParamInterface {
  id: string
  defaultValue: Nullable<number | string>
  min: Nullable<number>
  max: Nullable<number>
}

export interface SandboxPersonaOptionsInterface {
  forms: SandboxPersonaFormOptionInterface[]
  groups: SandboxPersonaFlagGroupInterface[]
  flags: SandboxPersonaFlagInterface[]
  params: SandboxPersonaParamInterface[]
}
