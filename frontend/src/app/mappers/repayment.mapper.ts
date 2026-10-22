import type { RepaymentDto } from '@/app/types/company/repayment-dto'
import type { RepaymentInterface } from '@/app/types/company/repayment-interface'

export class RepaymentMapper {
  static toEntity(data: RepaymentDto): RepaymentInterface {
    if (!data) {
      throw new Error('Repayment data is required')
    }

    return {
      fixedPayment: data.fixed.payment,
      fixedTotalInterest: data.fixed.total_interest,
      fixedWorstShare: data.fixed.worst3_share,
      isFixedComfortable: data.fixed.comfortable,
      inflowShare: data.from_inflows.share,
      inflowMinPayment: data.from_inflows.min_payment,
      inflowMaxPayment: data.from_inflows.max_payment,
      inflowMonths: data.from_inflows.months,
      inflowTotalInterest: data.from_inflows.total_interest,
      recommendation: data.recommendation,
      why: data.why,
    }
  }
}
