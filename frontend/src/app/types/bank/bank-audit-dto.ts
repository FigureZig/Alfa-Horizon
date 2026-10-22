import type { Nullable } from '@/app/types/nullable'

/** Проверка журнала аудита: GET v1/bank/audit — цепочка хэшей пересчитана с первой записи. */
export interface BankAuditDto {
  events: number
  intact: boolean
  broken_at: Nullable<number>
  last_hash: Nullable<string>
}
