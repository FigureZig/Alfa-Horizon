import type { CreditProductDto } from '@/app/types/company/credit-product-dto'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'

export class CreditProductMapper {
  static toEntity(data: CreditProductDto): CreditProductInterface {
    if (!data) {
      throw new Error('Credit product data is required')
    }

    return {
      id: data.id,
      code: data.product,
      name: data.name,
      amount: data.amount,
      currency: data.currency,
      rate: data.rate,
      isRateFrom: data.is_rate_from,
      termMonths: data.term_months,
      benefits: data.benefits,
      isPreliminary: data.is_preliminary,
      isRecommended: data.is_recommended,
    }
  }
}
