import type { SandboxPersonaCreateDto } from '@/app/types/sandbox/sandbox-persona-create-dto'
import type { SandboxPersonaDto } from '@/app/types/sandbox/sandbox-persona-dto'
import type { SandboxPersonaFormInterface } from '@/app/types/sandbox/sandbox-persona-form-interface'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

export class SandboxMapper {
  // Пока человек не заполнил обязательные числа, предпросмотр считается по значениям по умолчанию
  private static readonly DEFAULT_AGE_MONTHS = 36
  private static readonly DEFAULT_HEADCOUNT = 12
  private static readonly DEFAULT_INFLOW_AVG = 3_000_000

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
      badge: data.badge,
      roleTitle: data.role_title,
      about: data.about,
      companyInn: data.company_inn,
      companyName: data.companies?.find((company) => company.inn === data.company_inn)?.name ?? null,
      isCustom: data.custom,
      personInn: data.person_inn,
    }
  }

  static toPayload(form: SandboxPersonaFormInterface): SandboxPersonaCreateDto {
    // Пустые ответы в запрос не идут: бэкенд выведет их из простых (отрасль, кредиты, просрочки)
    return {
      kind: 'client',
      full_name: SandboxMapper.toOptionalText(form.fullName),
      organization: SandboxMapper.toOptionalText(form.organization),
      inn: SandboxMapper.toOptionalText(form.inn),
      form: form.form,
      industry: form.industry ?? undefined,
      structure: form.structure ?? undefined,
      accountant: form.accountant,
      representative: form.representative,
      seasonality: form.seasonality ?? undefined,
      stability: form.stability ?? undefined,
      trend: form.trend ?? undefined,
      channel: form.channel ?? undefined,
      loans: form.loans ?? undefined,
      delays: form.delays ?? undefined,
      age_months: form.ageMonths ?? SandboxMapper.DEFAULT_AGE_MONTHS,
      headcount: form.headcount ?? SandboxMapper.DEFAULT_HEADCOUNT,
      inflow_avg: form.inflowAvg ?? SandboxMapper.DEFAULT_INFLOW_AVG,
      inflow_cv: form.inflowCv ?? undefined,
      inflow_trend: form.inflowTrend ?? undefined,
      debt_load: form.debtLoad ?? undefined,
      overdue_days: form.overdueDays ?? undefined,
      bki_requests: form.bkiRequests ?? undefined,
      tax_debt: form.taxDebt ?? undefined,
      participants: form.participants ?? undefined,
      profit_margin: form.profitMargin ?? undefined,
      contract_price: form.contractPrice ?? undefined,
      flags: form.flags,
    }
  }

  // Пустой текст в запрос не идёт: бэкенд подставит своё значение
  private static toOptionalText(value: string): string | undefined {
    return value.trim() || undefined
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
