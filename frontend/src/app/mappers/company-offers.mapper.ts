import type { CompanyOffersDto } from '@/app/types/company/company-offers-dto'
import type { CompanyBlockerInterface } from '@/app/types/company/company-blocker-interface'

export class CompanyOffersMapper {
  static toBlockers(data: CompanyOffersDto): CompanyBlockerInterface[] {
    if (!data) {
      throw new Error('Company offers data is required')
    }

    return data.blockers.map((blocker) => ({ code: blocker.code, text: blocker.text }))
  }
}
