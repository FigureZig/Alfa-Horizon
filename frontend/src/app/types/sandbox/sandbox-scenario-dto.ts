import type { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { Nullable } from '@/app/types/nullable'

export interface SandboxScenarioStepDto {
  n: number
  user: Nullable<{ id: string; full_name: string; code: string }>
  action: string
  title: string
  button: Nullable<string>
  api: { method: string; path: string; body: Nullable<Record<string, unknown>> }
  expect_status: Nullable<ApplicationDetailStatusEnum>
  expect_http: number
  note: string
}

export interface SandboxScenarioDto {
  id: string
  title: string
  about: string
  company: { inn: string; name: string }
  users: string[]
  steps: SandboxScenarioStepDto[]
}
