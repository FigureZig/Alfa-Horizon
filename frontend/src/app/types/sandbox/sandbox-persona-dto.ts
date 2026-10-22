import type { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'

export interface SandboxPersonaDto {
  id: string
  code: string
  kind: SandboxPersonaKindEnum
  full_name: string
  inn: string
  organization: string
  scenario: string
  permissions: string
  profile: string
  registries: string
  preview: string
  login_label: string
  custom: boolean
  person_inn: string | null
  // Компании персоны: по ним в рабочем месте банка ИНН заявки получает название
  companies?: { inn: string, name: string }[]
}
