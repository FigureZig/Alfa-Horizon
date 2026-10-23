import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { applicationsService } from '@/app/services/application/applications.service'
import { ApplicationMapper } from '@/app/mappers/application.mapper'
import type { ApplicationInterface } from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * Заявка одним запросом, без живого потока и команд: для карточки «заявка в работе» на главной.
 * Ошибка не мешает странице — карточка просто не показывается.
 */
export function useApplicationSnapshot(applicationId: MaybeRefOrGetter<Nullable<string>>) {
  const $fetch = useApiFetch()

  const application = ref<Nullable<ApplicationInterface>>(null)
  const isLoading = ref(false)

  let lastRequestId = 0

  async function loadApplication() {
    const id = toValue(applicationId)
    const requestId = ++lastRequestId

    application.value = null

    if (!id) return

    isLoading.value = true

    try {
      const { data } = await applicationsService.fetchApplication($fetch, id)

      if (requestId !== lastRequestId) return

      application.value = ApplicationMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Application snapshot loading failed:', err)
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  watch(() => toValue(applicationId), loadApplication, { immediate: true })

  return { application, isLoading }
}
