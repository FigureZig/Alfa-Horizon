import type { BankApplicationDto } from '@/app/types/bank/bank-application-dto'
import type { BankApplicationInterface } from '@/app/types/bank/bank-application-interface'

export class BankApplicationMapper {
  static toEntity(data: BankApplicationDto): BankApplicationInterface {
    if (!data) {
      throw new Error('Bank application data is required')
    }

    return {
      id: data.id,
      inn: data.inn,
      companyName: data.company_name,
      status: data.status,
      product: data.request.product,
      amount: Number(data.offer?.amount ?? data.request.amount),
      outcome: data.outcome,
      decidedBy: data.decided_by,
      riskClass: data.risk_class,
      updatedAt: data.updated_at,
    }
  }
}
