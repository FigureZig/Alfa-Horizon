import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { applicationsService } from '@/app/services/application/applications.service'
import { ApplicationMapper } from '@/app/mappers/application.mapper'
import { ApplicationTaskMapper } from '@/app/mappers/application-task.mapper'
import type { Nullable } from '@/app/types/nullable'
import type { VoteItemInterface } from '@/app/types/application/vote-item-interface'

const TASK_ACTION_VOTE = 'vote'

/**
 * Заявки компании, где банк ждёт голос участника: задачи пользователя с действием «проголосовать»
 * и сами заявки с ходом голосования.
 */
export function useVoteTasks(inn: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()

  const items = ref<VoteItemInterface[]>([])
  const isLoading = ref(false)
  const error = ref(false)

  async function loadVotes() {
    if (isLoading.value) return

    isLoading.value = true
    error.value = false

    try {
      const { data } = await applicationsService.fetchTasks($fetch)
      const tasks = data.data
        .map((task) => ApplicationTaskMapper.toEntity(task))
        .filter((task) => task.action === TASK_ACTION_VOTE && task.companyInn === toValue(inn))

      const loaded = await Promise.all(tasks.map(async (task): Promise<Nullable<VoteItemInterface>> => {
        try {
          const { data: application } = await applicationsService.fetchApplication($fetch, task.applicationId)

          return { task, application: ApplicationMapper.toEntity(application.data) }
        } catch (err: unknown) {
          // Одна недоступная заявка не прячет остальные
          console.error('Vote application loading failed:', err)

          return null
        }
      }))

      items.value = loaded.filter((item): item is VoteItemInterface => item !== null)
    } catch (err: unknown) {
      console.error('Vote tasks loading failed:', err)
      error.value = true
    } finally {
      isLoading.value = false
    }
  }

  watch(() => toValue(inn), loadVotes, { immediate: true })

  return { items, isLoading, error, loadVotes }
}
