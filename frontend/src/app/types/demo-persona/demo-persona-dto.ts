import type { DemoPersonaRoleEnum } from '@/app/types/demo-persona/demo-persona-role-enum'

export interface DemoPersonaDto {
  inn: string
  first_name: string
  last_name: string
  initials: string
  organization_name: string
  role: DemoPersonaRoleEnum
  // Сегодняшняя дата мира (YYYY-MM-DD): по ней считаются прогноз, сроки и история
  today: string
  // Id пользователя в мире: у создателя своей компании вида c12
  user_id: string
}
