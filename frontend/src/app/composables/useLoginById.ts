import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getApiErrorCode } from '@/app/composables/useApiFetch'
import { useSession } from '@/app/composables/useSession'
import type { Nullable } from '@/app/types/nullable'

const ERROR_USER_NOT_FOUND = 'USER_NOT_FOUND'

/**
 * Вход по ID пользователя, ИНН человека или ИНН компании: поле на экране входа и вкладка панели проверяющего.
 * После входа переход по правам человека, как у карточки.
 */
export function useLoginById() {
  const { t } = useI18n({ useScope: 'global' })
  const { enterCabinetByLogin } = useSession()

  const login = ref('')
  const isSubmitting = ref(false)
  const errorMessage = ref<Nullable<string>>(null)

  // Возвращает true, если вход удался: вызывающий может закрыть панель
  async function submit(): Promise<boolean> {
    const value = login.value.trim()

    if (!value || isSubmitting.value) return false

    isSubmitting.value = true
    errorMessage.value = null

    try {
      await enterCabinetByLogin(value)

      return true
    } catch (err: unknown) {
      console.error('Login by ID failed:', err)

      errorMessage.value = getApiErrorCode(err) === ERROR_USER_NOT_FOUND
        ? t('reviewer.login.notFound')
        : t('reviewer.login.error')

      return false
    } finally {
      isSubmitting.value = false
    }
  }

  return { login, isSubmitting, errorMessage, submit }
}
