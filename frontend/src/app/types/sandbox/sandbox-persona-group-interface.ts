import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'
import type { Nullable } from '@/app/types/nullable'

/** Люди одной компании на экране входа; у сотрудников банка компании нет. */
export interface SandboxPersonaGroupInterface {
  key: string
  title: Nullable<string>
  isBank: boolean
  // Создатель своей компании: через его id компанию удаляют и правят
  ownerId: Nullable<string>
  personas: SandboxPersonaInterface[]
}
