import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { bankService } from '@/app/services/bank/bank.service'
import { BankQueueMapper } from '@/app/mappers/bank-queue.mapper'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import type { BankQueueItemInterface } from '@/app/types/bank/bank-queue-item-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * После решения — сразу следующая заявка в очереди, как в разборе входящих: сначала задачи этого сотрудника.
 */
export function useBankNextApplication(currentId: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()

  const nextItem = ref<Nullable<BankQueueItemInterface>>(null)
  // Решение по текущей заявке уже принято: показываем, куда дальше
  const isShown = ref(false)

  function isMine(item: BankQueueItemInterface): boolean {
    return item.availableActions.some((action) =>
      action === ApplicationActionEnum.Decide || action === ApplicationActionEnum.Confirm)
  }

  async function loadNext() {
    try {
      const { data } = await bankService.fetchQueue($fetch)
      const items = data.data
        .map((item) => BankQueueMapper.toEntity(item))
        .filter((item) => item.id !== toValue(currentId))

      nextItem.value = items.find(isMine) ?? items[0] ?? null
    } catch (err: unknown) {
      console.error('Next bank application loading failed:', err)
      nextItem.value = null
    } finally {
      isShown.value = true
    }
  }

  function reset() {
    nextItem.value = null
    isShown.value = false
  }

  watch(() => toValue(currentId), reset)

  return { nextItem, isShown, loadNext }
}
