import type { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'

export interface SandboxPersonaFormInterface {
  kind: SandboxPersonaKindEnum
  fullName: string
  inn: string
  organization: string
  code: string
  scenario: string
  permissions: string
  profile: string
  registries: string
  preview: string
  loginLabel: string
}
