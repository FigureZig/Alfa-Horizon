import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { clearSessionToken, setSessionToken, useApiFetch } from '@/app/composables/useApiFetch'
import { authService } from '@/app/services/auth/auth.service'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { CompanyAccessMapper } from '@/app/mappers/company-access.mapper'
import { SandboxMapper } from '@/app/mappers/sandbox.mapper'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { ApiResponse } from '@/app/types/api-response'
import type { AppLocale } from '@/app/i18n'
import type { CompanyAccessInterface } from '@/app/types/company/company-access-interface'
import type { SandboxLoginDto } from '@/app/types/sandbox/sandbox-login-dto'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

/**
 * Демо-сессия: вход персоной даёт JWT, его подставляет API-клиент; выход забывает токен.
 * Ошибки входа обрабатывает вызывающая страница.
 */
export function useSession() {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })
  const router = useRouter()

  // Вход принимает любой запрос входа: карточкой или по ID — ответ у них один
  async function signInWith(request: () => Promise<{ data: ApiResponse<SandboxLoginDto> }>) {
    const { data } = await request()

    setSessionToken(data.data.token)

    return {
      persona: SandboxMapper.toEntity(data.data.persona),
      companies: data.data.companies.map((company) => CompanyAccessMapper.toEntity(company)),
    }
  }

  function signIn(personaId: string) {
    return signInWith(() => sandboxService.loginAsPersona($fetch, personaId, locale.value as AppLocale))
  }

  async function loginAsPersona(personaId: string): Promise<SandboxPersonaInterface> {
    return (await signIn(personaId)).persona
  }

  // Куда вести после входа: решают права из ответа входа, а не роль на глаз
  function getEntryRoute(persona: SandboxPersonaInterface, companies: CompanyAccessInterface[]) {
    if (persona.kind === SandboxPersonaKindEnum.Bank) return { name: 'bank-queue', params: { inn: persona.inn } }

    const viewable = companies.find((company) => company.canView && company.inn === persona.inn)
      ?? companies.find((company) => company.canView)

    if (viewable) return { name: 'dashboard', params: { inn: viewable.inn } }

    // Участник ООО без доступа к счёту: только голосование
    const voting = companies.find((company) => company.canApprove)

    return voting
      ? { name: 'votes', params: { inn: voting.inn } }
      : { name: 'dashboard', params: { inn: persona.inn } }
  }

  // Вход и переход в рабочее место по правам человека
  async function enterCabinet(personaId: string): Promise<void> {
    const { persona, companies } = await signIn(personaId)

    await router.push(getEntryRoute(persona, companies))
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

  return { loginAsPersona, enterCabinet, logout }
}
