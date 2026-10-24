import { CompanyRoleEnum } from '@/app/types/company/company-role-enum'
import type { CompanyAccessDto, CompanyAccessRoleDto, MeDto } from '@/app/types/company/company-access-dto'
import type { CompanyAccessInterface, MeInterface } from '@/app/types/company/company-access-interface'

const ROLE_OWNER = 'owner'
const ROLE_DIRECTOR = 'eio'
const ROLE_PROXY = 'poa'
const ROLE_PARTICIPANT = 'participant'
const ROLE_BANK_ACCESS = 'bank_access'
// Доступ в интернет-банк, с которым человек готовит заявки, а не только смотрит
const WORKING_ACCESS_LEVELS = ['owner', 'prepare']

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
      role: CompanyAccessMapper.toRole(data.roles),
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

  // Главная роль человека в компании: ИП и директор важнее доверенности, доверенность — доступа в интернет-банк
  private static toRole(roles: CompanyAccessRoleDto[]): CompanyRoleEnum {
    const has = (name: string) => roles.some((role) => role.role === name)
    const access = roles.find((role) => role.role === ROLE_BANK_ACCESS)

    if (has(ROLE_OWNER)) return CompanyRoleEnum.Owner
    if (has(ROLE_DIRECTOR)) return CompanyRoleEnum.Director
    if (has(ROLE_PROXY)) return CompanyRoleEnum.Proxy
    if (access?.level && WORKING_ACCESS_LEVELS.includes(access.level)) return CompanyRoleEnum.Employee
    if (has(ROLE_PARTICIPANT)) return CompanyRoleEnum.Participant

    return CompanyRoleEnum.Viewer
  }
}
