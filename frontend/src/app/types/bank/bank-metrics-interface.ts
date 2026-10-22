import type { Nullable } from '@/app/types/nullable'

export interface BankPercentilesInterface {
  count: number
  medianSeconds: Nullable<number>
  p95Seconds: Nullable<number>
  targetSeconds: Nullable<number>
  withinTargetShare: Nullable<number>
}

export interface BankMetricsInterface {
  applicationsCount: number
  byStatus: Record<string, number>
  autoDecisions: number
  manualDecisions: number
  stpShare: Nullable<number>
  timeToDecision: BankPercentilesInterface
  manualReview: BankPercentilesInterface
  outcomes: Record<string, number>
  issuedCount: number
  issuedAmount: number
  slaBreaches: number
}
