import { onBeforeUnmount, reactive, ref, watch } from 'vue'
import debounce from 'lodash-es/debounce'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { bankService } from '@/app/services/bank/bank.service'
import { BankApplicationMapper } from '@/app/mappers/bank-application.mapper'
import type { BankApplicationInterface, BankApplicationsFilterInterface } from '@/app/types/bank/bank-application-interface'

const FILTER_DEBOUNCE = 300
// Реестр меняется, пока клиенты подают заявки, — обновляем его сами
const POLL_INTERVAL = 8000

/**
 * Реестр всех заявок банка с фильтрами. Первая загрузка и смена фильтра — со skeleton,
 * фоновое обновление — тихое, без мерцания.
 */
export function useBankApplications() {
  const $fetch = useApiFetch()

  const filter = reactive<BankApplicationsFilterInterface>({ status: null, decidedBy: null, query: '' })
  const applications = ref<BankApplicationInterface[]>([])
  const isLoading = ref(false)
  const error = ref(false)

  // Номер последнего запроса: ответы по прежним фильтрам отбрасываем
  let lastRequestId = 0

  async function loadApplications(isSilent = false) {
    const requestId = ++lastRequestId

    isLoading.value = !isSilent
    error.value = false

    try {
      const { data } = await bankService.fetchApplications($fetch, filter)

      if (requestId !== lastRequestId) return

      applications.value = data.data.map((item) => BankApplicationMapper.toEntity(item))
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Bank applications loading failed:', err)

      // Уже загруженный реестр остаётся: ошибка показывается, только если показывать нечего
      error.value = !applications.value.length
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  function refreshSilently() {
    loadApplications(true)
  }

  function reloadWithLoading() {
    loadApplications()
  }

  const reloadDebounced = debounce(reloadWithLoading, FILTER_DEBOUNCE)
  const pollTimer = setInterval(refreshSilently, POLL_INTERVAL)

  function resetFilter() {
    filter.status = null
    filter.decidedBy = null
    filter.query = ''
  }

  watch(filter, reloadDebounced, { deep: true })
  onBeforeUnmount(() => {
    clearInterval(pollTimer)
    reloadDebounced.cancel()
  })

  loadApplications()

  return { filter, applications, isLoading, error, loadApplications: reloadWithLoading, resetFilter }
}
