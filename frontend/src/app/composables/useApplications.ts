import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { applicationsService } from '@/app/services/application/applications.service'
import { ApplicationMapper } from '@/app/mappers/application.mapper'
import type { ApplicationInterface } from '@/app/types/application/application-interface'

/**
 * Заявки компании по ИНН, новые сверху.
 */
export function useApplications(inn: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()

  const applications = ref<ApplicationInterface[]>([])
  const isLoading = ref(false)
  const error = ref(false)

  // Номер последнего запроса: ответ по прежнему ИНН не должен перезаписать текущий
  let lastRequestId = 0

  async function loadApplications() {
    const requestId = ++lastRequestId

    isLoading.value = true
    error.value = false

    try {
      const { data } = await applicationsService.fetchApplications($fetch, toValue(inn))

      if (requestId !== lastRequestId) return

      applications.value = data.data.map((application) => ApplicationMapper.toEntity(application))
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Applications loading failed:', err)
      applications.value = []
      error.value = true
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  function onInnChange() {
    // Заявки прежней компании убираем сразу, не дожидаясь ответа
    applications.value = []
    loadApplications()
  }

  watch(() => toValue(inn), onInnChange, { immediate: true })

  return { applications, isLoading, error, loadApplications }
}
