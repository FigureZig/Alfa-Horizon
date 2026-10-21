import type { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'

export interface SandboxPersonaCreateDto {
  kind: SandboxPersonaKindEnum
  full_name: string
  organization: string
  code: string
  scenario: string
  permissions: string
  profile: string
  registries: string
  preview: string
  login_label: string
}
