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

export interface SandboxPersonaIndustryInterface {
  id: string
  title: string
  okved: string
  seasonality: string
  channel: string
}

export interface SandboxPersonaStructureInterface {
  id: string
  title: string
  means: string
  forms: LegalFormEnum[]
}

export interface SandboxPersonaPeopleInterface {
  id: string
  title: string
  means: string
  forms: LegalFormEnum[]
}

export interface SandboxPersonaChoiceInterface {
  id: string
  title: string
}

export interface SandboxPersonaChoicesInterface {
  seasonality: SandboxPersonaChoiceInterface[]
  stability: SandboxPersonaChoiceInterface[]
  trend: SandboxPersonaChoiceInterface[]
  channel: SandboxPersonaChoiceInterface[]
  loans: SandboxPersonaChoiceInterface[]
  delays: SandboxPersonaChoiceInterface[]
}

export interface SandboxPersonaOptionsInterface {
  forms: SandboxPersonaFormOptionInterface[]
  industries: SandboxPersonaIndustryInterface[]
  structures: SandboxPersonaStructureInterface[]
  people: SandboxPersonaPeopleInterface[]
  choices: SandboxPersonaChoicesInterface
  groups: SandboxPersonaFlagGroupInterface[]
  flags: SandboxPersonaFlagInterface[]
  params: SandboxPersonaParamInterface[]
}
