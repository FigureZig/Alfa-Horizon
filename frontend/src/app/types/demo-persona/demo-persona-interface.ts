import type { DemoPersonaRoleEnum } from '@/app/types/demo-persona/demo-persona-role-enum'

export interface DemoPersonaInterface {
  inn: string
  firstName: string
  lastName: string
  fullName: string
  initials: string
  organizationName: string
  role: DemoPersonaRoleEnum
  today: string
  userId: string
  // Сотрудник банка (специалист или риск-менеджер): у него рабочее место банка, а не кабинет компании
  isBankStaff: boolean
}
