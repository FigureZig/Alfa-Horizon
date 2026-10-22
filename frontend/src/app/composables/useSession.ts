import { useI18n } from 'vue-i18n'
import { clearSessionToken, setSessionToken, useApiFetch } from '@/app/composables/useApiFetch'
import { authService } from '@/app/services/auth/auth.service'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxMapper } from '@/app/mappers/sandbox.mapper'
import type { AppLocale } from '@/app/i18n'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

/**
 * Демо-сессия: вход персоной даёт JWT, его подставляет API-клиент; выход забывает токен.
 * Ошибки входа обрабатывает вызывающая страница.
 */
export function useSession() {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  async function loginAsPersona(personaId: string): Promise<SandboxPersonaInterface> {
    const { data } = await sandboxService.loginAsPersona($fetch, personaId, locale.value as AppLocale)

    setSessionToken(data.data.token)

    return SandboxMapper.toEntity(data.data.persona)
  }

  async function logout() {
    try {
      await authService.logout($fetch)
    } catch (err: unknown) {
      // Сессия на клиенте всё равно завершается: токен забываем в любом случае
      console.error('Logout request failed:', err)
    } finally {
      clearSessionToken()
    }
  }

  return { loginAsPersona, logout }
}
