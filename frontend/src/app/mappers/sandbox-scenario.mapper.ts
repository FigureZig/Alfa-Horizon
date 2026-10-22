import type { SandboxScenarioDto } from '@/app/types/sandbox/sandbox-scenario-dto'
import type { SandboxScenarioInterface } from '@/app/types/sandbox/sandbox-scenario-interface'

export class SandboxScenarioMapper {
  static toEntity(data: SandboxScenarioDto): SandboxScenarioInterface {
    return {
      id: data.id,
      title: data.title,
      about: data.about,
      company: data.company,
      users: data.users,
      steps: data.steps.map((step) => ({
        number: step.n,
        user: step.user ? { id: step.user.id, fullName: step.user.full_name, code: step.user.code } : null,
        action: step.action,
        title: step.title,
        button: step.button,
        request: step.api,
        expectedStatus: step.expect_status,
        expectedHttp: step.expect_http,
        note: step.note,
      })),
    }
  }
}
