import type { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { Nullable } from '@/app/types/nullable'

export interface SandboxPersonaInterface {
  id: string
  code: string
  kind: SandboxPersonaKindEnum
  fullName: string
  inn: string
  initials: string
  organization: string
  scenario: string
  permissions: string
  profile: string
  registries: string
  preview: string
  loginLabel: string
  badge: string
  roleTitle: string
  about: string
  companyInn: Nullable<string>
  companyName: Nullable<string>
  isCustom: boolean
  personInn: Nullable<string>
}
