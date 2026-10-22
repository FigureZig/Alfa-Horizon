import type { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { Nullable } from '@/app/types/nullable'

export interface SandboxScenarioStepInterface {
  number: number
  user: Nullable<{ id: string; fullName: string; code: string }>
  action: string
  title: string
  button: Nullable<string>
  request: { method: string; path: string; body: Nullable<Record<string, unknown>> }
  expectedStatus: Nullable<ApplicationDetailStatusEnum>
  expectedHttp: number
  note: string
}

export interface SandboxScenarioInterface {
  id: string
  title: string
  about: string
  company: { inn: string; name: string }
  users: string[]
  steps: SandboxScenarioStepInterface[]
}
