import type { Nullable } from '@/app/types/nullable'

export interface BankAuditInterface {
  eventsCount: number
  isIntact: boolean
  brokenAt: Nullable<number>
  lastHash: Nullable<string>
}
