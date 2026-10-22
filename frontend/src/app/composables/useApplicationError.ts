import { useI18n } from 'vue-i18n'
import { getApiErrorCode } from '@/app/composables/useApiFetch'
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
}

export function useApplicationError() {
  const { t } = useI18n({ useScope: 'global' })

  function getApplicationErrorMessage(err: unknown): string {
    const code = getApiErrorCode(err)

    return t(`application.errors.${(code && ERROR_KEYS[code]) || 'generic'}`)
  }

  return { getApplicationErrorMessage }
}
