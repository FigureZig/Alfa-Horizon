import type { Nullable } from '@/app/types/nullable'

// Кто сделал: имя и роль. client — человек компании, bank — сотрудник банка, system — автоматика банка
export interface ApplicationEventAuthorDto {
  kind: 'client' | 'bank' | 'system'
  name: string
  role?: Nullable<string>
  title?: Nullable<string>
  detail?: Nullable<string>
}

/** Запись истории заявки: GET v1/applications/{id}/events и события потока .../stream. */
export interface ApplicationEventDto {
  id: number
  at: string
  type: string
  actor: string
  payload: Record<string, unknown>
  by?: ApplicationEventAuthorDto
}
