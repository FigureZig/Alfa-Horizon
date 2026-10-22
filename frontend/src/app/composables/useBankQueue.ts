import { onBeforeUnmount, ref } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { bankService } from '@/app/services/bank/bank.service'
import { BankQueueMapper } from '@/app/mappers/bank-queue.mapper'
import type { BankQueueItemInterface } from '@/app/types/bank/bank-queue-item-interface'

// Очередь меняется, пока клиенты подают заявки, — обновляем её сами
const POLL_INTERVAL = 5000

/**
 * Очередь исключений банка: заявки, которые движок не смог решить автоматически.
 * Первая загрузка со skeleton, дальше обновляется тихо, без мерцания.
 */
export function useBankQueue() {
  const $fetch = useApiFetch()

  const queue = ref<BankQueueItemInterface[]>([])
  const isLoading = ref(false)
  const error = ref(false)

  let isRequestRunning = false

  async function loadQueue() {
    if (isRequestRunning) return

    isRequestRunning = true
    isLoading.value = true

    try {
      const { data } = await bankService.fetchQueue($fetch)

      queue.value = data.data.map((item) => BankQueueMapper.toEntity(item))
      error.value = false
    } catch (err: unknown) {
      console.error('Bank queue loading failed:', err)

      // Уже загруженная очередь остаётся: ошибка показывается, только если показывать нечего
      error.value = !queue.value.length
    } finally {
      isRequestRunning = false
      isLoading.value = false
    }
  }

  const pollTimer = setInterval(loadQueue, POLL_INTERVAL)

  onBeforeUnmount(() => clearInterval(pollTimer))

  loadQueue()

  return { queue, isLoading, error, loadQueue }
}
