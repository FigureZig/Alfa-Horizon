import type { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'

export interface SandboxPersonaDto {
  id: string
  code: string
  kind: SandboxPersonaKindEnum
  full_name: string
  organization: string
  scenario: string
  permissions: string
  profile: string
  registries: string
  preview: string
  login_label: string
}
