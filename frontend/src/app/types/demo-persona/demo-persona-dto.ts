import type { DemoPersonaRoleEnum } from '@/app/types/demo-persona/demo-persona-role-enum'

export interface DemoPersonaDto {
  inn: string
  first_name: string
  last_name: string
  initials: string
  organization_name: string
  role: DemoPersonaRoleEnum
}
