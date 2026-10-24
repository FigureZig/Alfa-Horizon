import { ref, toValue } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useScenarioRun } from '@/app/composables/useScenarioRun'
import { useApplicationError } from '@/app/composables/useApplicationError'
import { bankService } from '@/app/services/bank/bank.service'
import { BankDecisionActionEnum } from '@/app/types/bank/bank-decision-action-enum'
import type { BankConfirmFormInterface, BankDecisionFormInterface } from '@/app/types/bank/bank-decision-form-interface'
import type { Nullable } from '@/app/types/nullable'

type BankCommand = BankDecisionActionEnum | 'confirm' | 'return'

/**
 * Решения сотрудника банка по заявке: специалист одобряет, отказывает или запрашивает данные,
 * риск-менеджер подтверждает или возвращает одобрение. `onDone` вызывается после успешной команды —
 * страница обновляет заявку и досье.
 */
export function useBankDecision(applicationId: MaybeRefOrGetter<string>, onDone: () => void) {
  const $fetch = useApiFetch()
  const toast = useToast()
  const { t } = useI18n({ useScope: 'global' })
  const { getApplicationErrorMessage } = useApplicationError()
  const { reportAction } = useScenarioRun()

  const pendingCommand = ref<Nullable<BankCommand>>(null)

  async function run(command: BankCommand, request: () => Promise<unknown>): Promise<boolean> {
    if (pendingCommand.value) return false

    pendingCommand.value = command

    try {
      await request()
      reportAction(command, toValue(applicationId))

      toast.add({
        severity: 'success',
        summary: t('toast.success'),
        detail: t(`toast.bank.${command}`),
        life: 4000,
      })

      onDone()

      return true
    } catch (err: unknown) {
      console.error(`Bank command ${command} failed:`, err)

      toast.add({
        severity: 'error',
        summary: t('toast.error'),
        detail: getApplicationErrorMessage(err),
        life: 6000,
      })

      // Заявку мог рассмотреть коллега — подтягиваем свежее состояние
      onDone()

      return false
    } finally {
      pendingCommand.value = null
    }
  }

  function decide(form: BankDecisionFormInterface) {
    const isApprove = form.action === BankDecisionActionEnum.Approve
    const isRequestInfo = form.action === BankDecisionActionEnum.RequestInfo

    return run(form.action, () =>
      bankService.decide($fetch, toValue(applicationId), {
        action: form.action,
        // Сумма и срок нужны только при одобрении: цена остаётся прежней, меняются условия
        amount: isApprove ? form.amount ?? undefined : undefined,
        term_months: isApprove ? form.termMonths ?? undefined : undefined,
        asks: isRequestInfo && form.asks.length ? form.asks : undefined,
        comment: form.comment.trim() || undefined,
      }))
  }

  function confirm(form: BankConfirmFormInterface) {
    return run(form.isApproved ? 'confirm' : 'return', () =>
      bankService.confirm($fetch, toValue(applicationId), {
        approve: form.isApproved,
        comment: form.comment.trim() || undefined,
      }))
  }

  return { pendingCommand, decide, confirm }
}
