import type { CatalogProductDto } from '@/app/types/catalog/catalog-product-dto'
import type { CatalogProductInterface } from '@/app/types/catalog/catalog-product-interface'

export class CatalogProductMapper {
  static toEntity(data: CatalogProductDto): CatalogProductInterface {
    if (!data) {
      throw new Error('Catalog product data is required')
    }

    return {
      code: data.id,
      name: data.name,
      benefits: data.benefits,
      amountMin: data.amount_min,
      amountMax: data.amount_max,
      termMonthsMin: data.term_months_min,
      termMonthsMax: data.term_months_max,
      rateFrom: data.rate_from,
      decisionText: data.decision_text,
      goals: data.goals,
      repayment: data.repayment,
    }
  }
}
