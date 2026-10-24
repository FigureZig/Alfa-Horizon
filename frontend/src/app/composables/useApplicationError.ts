import { useI18n } from 'vue-i18n'
import { getApiErrorCode, getApiProblem } from '@/app/composables/useApiFetch'
import { ApiErrorCodeEnum } from '@/app/types/api-error-code-enum'

// Коды ошибок команд заявки → ключ локализованного текста: технические сообщения API пользователю не показываем
const ERROR_KEYS: Record<string, string> = {
  [ApiErrorCodeEnum.Forbidden]: 'forbidden',
  [ApiErrorCodeEnum.InvalidTransition]: 'statusChanged',
  [ApiErrorCodeEnum.InvalidStatus]: 'statusChanged',
  [ApiErrorCodeEnum.CannotWithdraw]: 'cannotWithdraw',
  [ApiErrorCodeEnum.BkiPending]: 'bkiPending',
  [ApiErrorCodeEnum.SourceWait]: 'sourceWait',
  [ApiErrorCodeEnum.AwaitingSecondKey]: 'awaitingSecondKey',
  [ApiErrorCodeEnum.NothingToConfirm]: 'nothingToConfirm',
  [ApiErrorCodeEnum.SamePerson]: 'samePerson',
  [ApiErrorCodeEnum.BankOnly]: 'bankOnly',
  [ApiErrorCodeEnum.RoleRequired]: 'roleRequired',
  [ApiErrorCodeEnum.AmountRequired]: 'amountRequired',
  [ApiErrorCodeEnum.GoalRequired]: 'goalRequired',
}

export function useApplicationError() {
  const { t } = useI18n({ useScope: 'global' })

  function getApplicationErrorMessage(err: unknown): string {
    const code = getApiErrorCode(err)

    // Подбор без продукта не нашёл варианта: текст с бэкенда уже человеческий, в нём — что мешает
    if (code === ApiErrorCodeEnum.NoProductForGoal) {
      const problem = getApiProblem(err)
      const blockers = Array.isArray(problem?.blockers) ? (problem.blockers as { text: string }[]) : []

      return [problem?.detail, blockers[0]?.text].filter(Boolean).join(': ')
    }

    if (code && ERROR_KEYS[code]) return t(`application.errors.${ERROR_KEYS[code]}`)

    // Незнакомый код: бэкенд объясняет ошибку по-человечески — показываем его текст, а не общее «не удалось»
    const detail = getApiProblem(err)?.detail

    return typeof detail === 'string' && detail
      ? detail.charAt(0).toUpperCase() + detail.slice(1)
      : t('application.errors.generic')
  }

  return { getApplicationErrorMessage }
}
