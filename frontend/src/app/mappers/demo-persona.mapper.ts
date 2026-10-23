import { DemoPersonaRoleEnum } from '@/app/types/demo-persona/demo-persona-role-enum'
import type { DemoPersonaDto } from '@/app/types/demo-persona/demo-persona-dto'
import type { DemoPersonaInterface } from '@/app/types/demo-persona/demo-persona-interface'

export class DemoPersonaMapper {
  static toEntity(data: DemoPersonaDto): DemoPersonaInterface {
    if (!data) {
      throw new Error('Demo persona data is required')
    }

    return {
      inn: data.inn,
      firstName: data.first_name,
      lastName: data.last_name,
      fullName: [data.first_name, data.last_name].filter(Boolean).join(' '),
      initials: data.initials,
      organizationName: data.organization_name,
      role: data.role,
      today: data.today,
      userId: data.user_id,
      isBankStaff: data.role !== DemoPersonaRoleEnum.Client,
    }
  }
}
