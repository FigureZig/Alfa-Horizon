import type { SandboxPersonaCreateDto } from '@/app/types/sandbox/sandbox-persona-create-dto'
import type { SandboxPersonaDto } from '@/app/types/sandbox/sandbox-persona-dto'
import type { SandboxPersonaFormInterface } from '@/app/types/sandbox/sandbox-persona-form-interface'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'
import type { Nullable } from '@/app/types/nullable'

export class SandboxMapper {
  static toEntity(data: SandboxPersonaDto): SandboxPersonaInterface {
    if (!data) {
      throw new Error('Sandbox persona data is required')
    }

    return {
      id: data.id,
      code: data.code,
      kind: data.kind,
      fullName: data.full_name,
      inn: data.inn,
      initials: SandboxMapper.toInitials(data.full_name),
      organization: data.organization,
      scenario: data.scenario,
      permissions: data.permissions,
      profile: data.profile,
      registries: data.registries,
      preview: data.preview,
      loginLabel: data.login_label,
      isCustom: data.custom,
      personInn: data.person_inn,
    }
  }

  static toPayload(form: SandboxPersonaFormInterface): SandboxPersonaCreateDto {
    return {
      full_name: form.fullName.trim(),
      inn: SandboxMapper.toOptionalText(form.inn),
      organization: SandboxMapper.toOptionalText(form.organization),
      form: form.form,
      okved: form.okved.trim(),
      okved_name: form.okvedName.trim(),
      age_months: SandboxMapper.toRequiredNumber(form.ageMonths),
      headcount: SandboxMapper.toRequiredNumber(form.headcount),
      inflow_avg: SandboxMapper.toRequiredNumber(form.inflowAvg),
      inflow_cv: SandboxMapper.toRequiredNumber(form.inflowCv),
      inflow_trend: SandboxMapper.toRequiredNumber(form.inflowTrend),
      debt_load: SandboxMapper.toRequiredNumber(form.debtLoad),
      overdue_days: SandboxMapper.toRequiredNumber(form.overdueDays),
      bki_requests: SandboxMapper.toRequiredNumber(form.bkiRequests),
      tax_debt: SandboxMapper.toRequiredNumber(form.taxDebt),
      participants: SandboxMapper.toRequiredNumber(form.participants),
      profit_margin: SandboxMapper.toRequiredNumber(form.profitMargin),
      contract_price: form.contractPrice ?? undefined,
      flags: form.flags,
    }
  }

  // Пустой текст в запрос не идёт: бэкенд подставит своё значение
  private static toOptionalText(value: string): string | undefined {
    return value.trim() || undefined
  }

  private static toRequiredNumber(value: Nullable<number>): number {
    if (value === null) {
      throw new Error('Persona form number is required')
    }

    return value
  }

  private static toInitials(fullName: string): string {
    return fullName
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0].toUpperCase())
      .join('')
  }
}
