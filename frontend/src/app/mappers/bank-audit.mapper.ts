import type { BankAuditDto } from '@/app/types/bank/bank-audit-dto'
import type { BankAuditInterface } from '@/app/types/bank/bank-audit-interface'

export class BankAuditMapper {
  static toEntity(data: BankAuditDto): BankAuditInterface {
    if (!data) {
      throw new Error('Bank audit data is required')
    }

    return {
      eventsCount: data.events,
      isIntact: data.intact,
      brokenAt: data.broken_at,
      lastHash: data.last_hash,
    }
  }
}
