import type { SandboxPersonaCreateDto } from '@/app/types/sandbox/sandbox-persona-create-dto'
import type { SandboxPersonaDto } from '@/app/types/sandbox/sandbox-persona-dto'
import type { SandboxPersonaFormInterface } from '@/app/types/sandbox/sandbox-persona-form-interface'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

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
    }
  }

  static toPayload(form: SandboxPersonaFormInterface): SandboxPersonaCreateDto {
    return {
      kind: form.kind,
      full_name: form.fullName.trim(),
      inn: form.inn.trim(),
      organization: form.organization.trim(),
      code: form.code.trim(),
      scenario: form.scenario.trim(),
      permissions: form.permissions.trim(),
      profile: form.profile.trim(),
      registries: form.registries.trim(),
      preview: form.preview.trim(),
      login_label: form.loginLabel.trim(),
    }
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
