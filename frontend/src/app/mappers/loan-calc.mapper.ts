import type { LoanCalcDto, LoanCalcRequestDto } from '@/app/types/catalog/loan-calc-dto'
import type { LoanCalcInterface, LoanCalcParamsInterface } from '@/app/types/catalog/loan-calc-interface'

export class LoanCalcMapper {
  static toEntity(data: LoanCalcDto): LoanCalcInterface {
    if (!data) {
      throw new Error('Loan calculation data is required')
    }

    const parts = data.rate_parts

    return {
      rate: Number(data.rate),
      keyRate: parts ? Number(parts.key_rate) : null,
      industrySpread: parts ? Number(parts.industry) : null,
      riskSpread: parts ? Number(parts.risk) : null,
      riskClass: parts?.risk_class ?? null,
      repayment: data.repayment,
      payment: Number(data.payment),
      overpayment: data.overpayment === null ? null : Number(data.overpayment),
      usageExample: data.usage_example
        ? {
          amount: Number(data.usage_example.amount),
          days: data.usage_example.days,
          interest: Number(data.usage_example.interest),
          text: data.usage_example.text,
        }
        : null,
      schedule: data.schedule.map((row) => ({
        number: row.n,
        payment: Number(row.payment),
        interest: Number(row.interest),
        principal: Number(row.principal),
        balance: Number(row.balance),
      })),
    }
  }

  static toPayload(params: LoanCalcParamsInterface): LoanCalcRequestDto {
    return {
      amount: params.amount,
      term_months: params.termMonths,
      product: params.product,
      section: params.section ?? undefined,
      risk_class: params.riskClass,
      segment: params.segment,
    }
  }
}
