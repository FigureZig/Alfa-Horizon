import type { BankMetricsDto, BankPercentilesDto } from '@/app/types/bank/bank-metrics-dto'
import type { BankMetricsInterface, BankPercentilesInterface } from '@/app/types/bank/bank-metrics-interface'

export class BankMetricsMapper {
  static toEntity(data: BankMetricsDto): BankMetricsInterface {
    if (!data) {
      throw new Error('Bank metrics data is required')
    }

    return {
      applicationsCount: data.applications,
      byStatus: data.by_status,
      autoDecisions: data.decisions.auto,
      manualDecisions: data.decisions.manual,
      stpShare: data.decisions.stp_share,
      timeToDecision: BankMetricsMapper.toPercentiles(data.time_to_decision),
      manualReview: BankMetricsMapper.toPercentiles(data.manual_review),
      outcomes: data.outcomes,
      issuedCount: data.issued.count,
      issuedAmount: Number(data.issued.amount),
      slaBreaches: data.sla_breaches,
    }
  }

  private static toPercentiles(data: BankPercentilesDto): BankPercentilesInterface {
    return {
      count: data.count,
      medianSeconds: data.p50,
      p95Seconds: data.p95,
      targetSeconds: data.target,
      withinTargetShare: data.within_target,
    }
  }
}
