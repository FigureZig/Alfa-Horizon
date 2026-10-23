import type { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { Nullable } from '@/app/types/nullable'

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
  // Карточка входа простым языком: значок роли, должность и пара фраз о бизнесе
  badge: string
  role_title: string
  about: string
  company_inn: Nullable<string>
  custom: boolean
  person_inn: Nullable<string>
  // Компании персоны: по ним в рабочем месте банка ИНН заявки получает название
  companies?: { inn: string, name: string }[]
}
