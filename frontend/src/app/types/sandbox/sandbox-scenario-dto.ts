export interface SandboxScenarioStepDto {
  n: number
  user: { id: string; full_name: string; code: string } | null
  action: string
  title: string
  button: string | null
  api: { method: string; path: string; body: Record<string, unknown> | null }
  expect_status: string | null
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
