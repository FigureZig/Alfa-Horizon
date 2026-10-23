import type { CompanyAccessDto, MeDto } from '@/app/types/company/company-access-dto'
import type { CompanyAccessInterface, MeInterface } from '@/app/types/company/company-access-interface'

const ROLE_PARTICIPANT = 'participant'

export class CompanyAccessMapper {
  static toEntity(data: CompanyAccessDto): CompanyAccessInterface {
    if (!data) {
      throw new Error('Company access data is required')
    }

    return {
      inn: data.inn,
      name: data.name,
      shortName: data.short_name,
      canView: data.can.view,
      canApprove: data.can.approve,
      share: data.roles.find((role) => role.role === ROLE_PARTICIPANT)?.share ?? null,
    }
  }

  static toMe(data: MeDto): MeInterface {
    if (!data) {
      throw new Error('Me data is required')
    }

    return {
      personInn: data.persona.person_inn,
      companies: data.companies.map((company) => CompanyAccessMapper.toEntity(company)),
    }
  }
}
