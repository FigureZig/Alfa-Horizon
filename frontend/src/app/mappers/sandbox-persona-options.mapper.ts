import type { SandboxPersonaOptionsDto, SandboxPersonaParamDto } from '@/app/types/sandbox/sandbox-persona-options-dto'
import type {
  SandboxPersonaOptionsInterface,
  SandboxPersonaParamInterface,
} from '@/app/types/sandbox/sandbox-persona-options-interface'

export class SandboxPersonaOptionsMapper {
  static toEntity(data: SandboxPersonaOptionsDto): SandboxPersonaOptionsInterface {
    if (!data) {
      throw new Error('Sandbox persona options data is required')
    }

    return {
      forms: data.forms.map((form) => ({ id: form.id, title: form.title })),
      groups: data.groups.map((group) => ({ id: group.id, title: group.title })),
      flags: data.flags.map((flag) => ({
        id: flag.id,
        group: flag.group,
        title: flag.title,
        effect: flag.effect,
        forms: flag.forms,
      })),
      industries: data.industries.map((industry) => ({
        id: industry.id,
        title: industry.title,
        okved: industry.okved,
        seasonality: industry.seasonality,
        channel: industry.channel,
      })),
      structures: data.structures.map((structure) => ({ ...structure })),
      people: data.people.map((person) => ({ ...person })),
      choices: data.choices,
      params: data.params.map((param) => SandboxPersonaOptionsMapper.toParam(param)),
    }
  }

  private static toParam(param: SandboxPersonaParamDto): SandboxPersonaParamInterface {
    // Строгая нижняя граница (gt) у целых — это граница + 1
    const strictMin = param.gt === undefined ? null : param.gt + (param.type === 'integer' ? 1 : 0)

    return {
      id: param.id,
      defaultValue: param.default,
      min: param.ge ?? strictMin,
      max: param.le ?? null,
    }
  }
}
