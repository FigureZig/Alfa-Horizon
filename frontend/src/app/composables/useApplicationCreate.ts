import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useScenarioRun } from '@/app/composables/useScenarioRun'
import { useApplicationError } from '@/app/composables/useApplicationError'
import { applicationsService } from '@/app/services/application/applications.service'
import { ApplicationMapper } from '@/app/mappers/application.mapper'
import type { ApplicationFormInterface } from '@/app/types/application/application-form-interface'
import type { ApplicationInterface } from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

// Ключ идемпотентности: повтор подачи с тем же ключом не создаёт дублей
export function createIdempotencyKey(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

/**
 * Подача заявки «в один клик»: черновик → подача. Если подача не прошла, черновик остаётся —
 * пользователь доведёт его на странице заявки.
 */
export function useApplicationCreate(inn: string) {
  const $fetch = useApiFetch()
  const toast = useToast()
  const { t } = useI18n({ useScope: 'global' })
  const { getApplicationErrorMessage } = useApplicationError()
  const { reportAction } = useScenarioRun()

  const isSubmitting = ref(false)
  const errorMessage = ref<Nullable<string>>(null)

  async function createAndSubmit(form: ApplicationFormInterface): Promise<Nullable<ApplicationInterface>> {
    if (isSubmitting.value) return null

    isSubmitting.value = true
    errorMessage.value = null

    let draft: ApplicationInterface

    try {
      const { data } = await applicationsService.createApplication($fetch, ApplicationMapper.toCreatePayload(inn, form))

      draft = ApplicationMapper.toEntity(data.data)
      reportAction('create', draft.id, draft.status)
    } catch (err: unknown) {
      console.error('Application creation failed:', err)
      errorMessage.value = getApplicationErrorMessage(err)
      isSubmitting.value = false

      return null
    }

    try {
      const { data } = await applicationsService.submitApplication($fetch, draft.id, createIdempotencyKey())
      const submitted = ApplicationMapper.toEntity(data.data)

      reportAction('submit', submitted.id, submitted.status)

      toast.add({
        severity: 'success',
        summary: t('toast.success'),
        detail: t('toast.application.submit'),
        life: 4000,
      })

      return submitted
    } catch (err: unknown) {
      console.error('Application submit failed:', err)

      toast.add({
        severity: 'error',
        summary: t('toast.error'),
        detail: t('application.errors.draftSaved'),
        life: 6000,
      })

      return draft
    } finally {
      isSubmitting.value = false
    }
  }

  return { isSubmitting, errorMessage, createAndSubmit }
}
