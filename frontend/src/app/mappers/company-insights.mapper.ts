import { CreditProductMapper } from '@/app/mappers/credit-product.mapper'
import type { CompanyInsightsDto } from '@/app/types/company/company-insights-dto'
import type { CashForecastInterface } from '@/app/types/company/cash-forecast-interface'
import type { Nullable } from '@/app/types/nullable'

export class CompanyInsightsMapper {
  static toEntity(data: CompanyInsightsDto): Nullable<CashForecastInterface> {
    if (!data) {
      throw new Error('Company insights data is required')
    }

    const forecast = data.cash_forecast

    if (!forecast) return null

    return {
      status: forecast.status,
      horizonDays: forecast.horizon_days,
      currency: forecast.currency,
      points: forecast.points.map((point) => ({
        date: point.date,
        balance: point.balance,
      })),
      cashGap: forecast.cash_gap
        ? { date: forecast.cash_gap.date, amount: forecast.cash_gap.amount }
        : null,
      creditLine: forecast.credit_line ?? null,
      dailyInflow: forecast.daily_inflow ?? null,
      regularOutflows: (forecast.regular_outflows ?? []).map((outflow) => ({
        title: outflow.title,
        day: outflow.day,
        amount: outflow.amount,
      })),
      offer: data.offer
        ? { ...CreditProductMapper.toEntity(data.offer), cover: data.offer.cover ?? null }
        : null,
      contract: data.contract
        ? {
          regNum: data.contract.reg_num,
          customer: data.contract.customer,
          price: data.contract.price,
          advancePercent: data.contract.advance_percent,
          endDate: data.contract.end_date,
        }
        : null,
      operations: forecast.operations.map((operation) => ({
        id: operation.id,
        date: operation.date,
        title: operation.title,
        amount: operation.amount,
      })),
    }
  }
}
