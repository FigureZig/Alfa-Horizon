import type { Nullable } from '@/app/types/nullable'

export interface BankPercentilesDto {
  count: number
  p50: Nullable<number>
  p95: Nullable<number>
  target: Nullable<number>
  within_target: Nullable<number>
}

/**
 * Как работает конвейер: GET v1/bank/metrics. Время — в секундах, доли — от 0 до 1,
 * сумма выдач приходит строкой.
 */
export interface BankMetricsDto {
  applications: number
  by_status: Record<string, number>
  decisions: {
    auto: number
    manual: number
    stp_share: Nullable<number>
  }
  time_to_decision: BankPercentilesDto
  manual_review: BankPercentilesDto
  outcomes: Record<string, number>
  issued: {
    count: number
    amount: string
  }
  sla_breaches: number
}
