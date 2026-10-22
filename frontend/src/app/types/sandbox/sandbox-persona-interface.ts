import type { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'

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
}
