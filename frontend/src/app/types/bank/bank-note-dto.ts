import type { ApplicationOfferDto } from '@/app/types/application/application-dto'
import type { Nullable } from '@/app/types/nullable'

export interface BankSecondKeyDto {
  by: string
  at: string
  action: string
  comment: Nullable<string>
}

/**
 * Решение сотрудника банка по заявке: специалиста или риск-менеджера (второй ключ).
 * `limit` — полномочия специалиста, ₽; `offer` — условия, которые он одобрил.
 */
export interface BankNoteDto {
  at: string
  by: string
  action: string
  comment?: Nullable<string>
  limit?: Nullable<number>
  offer?: Nullable<ApplicationOfferDto>
  second_key?: Nullable<BankSecondKeyDto>
}
