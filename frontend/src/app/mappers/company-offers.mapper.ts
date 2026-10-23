import type { CompanyOfferOptionDto, CompanyOffersDto } from '@/app/types/company/company-offers-dto'
import type { CompanyBlockerInterface } from '@/app/types/company/company-blocker-interface'
import type { CompanyOfferOptionInterface, CompanyOffersInterface } from '@/app/types/company/company-offers-interface'

const LABEL_RANKS: Record<string, number> = {
  PREAPPROVED: 0,
  CONDITIONAL: 1,
  REVIEW: 2,
  UNAVAILABLE: 3,
}

const REVOLVING = 'revolving'

export class CompanyOffersMapper {
  static toBlockers(data: CompanyOffersDto): CompanyBlockerInterface[] {
    if (!data) {
      throw new Error('Company offers data is required')
    }

    return data.blockers.map((blocker) => ({ code: blocker.code, text: blocker.text }))
  }

  static toEntity(data: CompanyOffersDto): CompanyOffersInterface {
    return {
      blockers: CompanyOffersMapper.toBlockers(data),
      options: data.options
        .map((option) => CompanyOffersMapper.toOption(option))
        .sort((first, second) => first.rank - second.rank || Number(second.isRecommended) - Number(first.isRecommended)),
    }
  }

  private static toOption(option: CompanyOfferOptionDto): CompanyOfferOptionInterface {
    const terms = option.offer

    return {
      code: option.product,
      name: option.name,
      isAvailable: option.available,
      rank: LABEL_RANKS[option.label] ?? LABEL_RANKS.UNAVAILABLE,
      label: option.label,
      isRevolving: option.repayment === REVOLVING,
      maxAmount: option.max_amount === null ? null : Number(option.max_amount),
      amount: terms ? Number(terms.amount) : null,
      termMonths: terms?.term_months ?? null,
      rate: terms ? Number(terms.rate) : null,
      payment: terms ? Number(terms.payment) : null,
      needs: option.needs.map((need) => (typeof need === 'string' ? need : need.text)),
      reasons: option.why,
      isRecommended: option.recommended,
    }
  }
}
