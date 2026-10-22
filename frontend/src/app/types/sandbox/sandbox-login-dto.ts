import type { SandboxPersonaDto } from '@/app/types/sandbox/sandbox-persona-dto'

/**
 * Ответ входа персоной: POST v1/sandbox/personas/{id}/login.
 * `loading` — банк ещё собирает данные компаний; кабинет повторит запросы сам.
 */
export interface SandboxLoginDto {
  token: string
  token_type: 'Bearer'
  persona: SandboxPersonaDto
  loading: boolean
}
