import { onBeforeUnmount, ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import debounce from 'lodash-es/debounce'
import { getApiProblem, useApiFetch } from '@/app/composables/useApiFetch'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxMapper } from '@/app/mappers/sandbox.mapper'
import { SandboxPersonaPreviewMapper } from '@/app/mappers/sandbox-persona-preview.mapper'
import { ApiErrorCodeEnum } from '@/app/types/api-error-code-enum'
import type { ApiProblemDto } from '@/app/types/api-problem-dto'
import type { AppLocale } from '@/app/i18n'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxPersonaFormInterface } from '@/app/types/sandbox/sandbox-persona-form-interface'
import type { SandboxPersonaPreviewInterface } from '@/app/types/sandbox/sandbox-persona-preview-interface'

const PREVIEW_DEBOUNCE = 300

const CONFLICT_CODES: string[] = [
  ApiErrorCodeEnum.AnswersConflict,
  ApiErrorCodeEnum.StructureConflict,
  ApiErrorCodeEnum.StructureNotApplicable,
]

// Ответы, у которых показать конфликт: бэкенд называет их у ANSWERS_CONFLICT, у остальных это устройство и флаги
function getConflictFields(code: string, problem: ApiProblemDto): string[] {
  if (Array.isArray(problem.fields)) return problem.fields as string[]

  const flags = Array.isArray(problem.flags) ? (problem.flags as string[]).map((flag) => `flags.${flag}`) : []

  return code === ApiErrorCodeEnum.AnswersConflict ? [] : ['structure', ...flags]
}

// Противоречие в ответах: текст для людей и ответы конструктора, у которых его показать
export interface SandboxPersonaConflictInterface {
  message: string
  fields: string[]
}

/**
 * Живой предпросмотр своей компании: что банк скажет и почему. Пересчитывается при каждом изменении ответов;
 * последняя удачная картина остаётся на экране, пока считается новая или ответы противоречат друг другу.
 */
export function useSandboxPersonaPreview(
  form: MaybeRefOrGetter<SandboxPersonaFormInterface>,
  personaId: MaybeRefOrGetter<Nullable<string>>,
  // Пока человек отвечает на первые вопросы, банк не считает: предпросмотр появляется после них
  isEnabled: MaybeRefOrGetter<boolean> = true,
) {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const preview = ref<Nullable<SandboxPersonaPreviewInterface>>(null)
  const conflict = ref<Nullable<SandboxPersonaConflictInterface>>(null)
  const isLoading = ref(false)
  const error = ref(false)

  // Номер последнего запроса: ответы по прежним ответам формы отбрасываем
  let lastRequestId = 0

  async function loadPreview() {
    const requestId = ++lastRequestId

    isLoading.value = true
    error.value = false

    try {
      const { data } = await sandboxService.previewPersona(
        $fetch,
        SandboxMapper.toPayload(toValue(form)),
        locale.value as AppLocale,
        toValue(personaId) ?? undefined,
      )

      if (requestId !== lastRequestId) return

      preview.value = SandboxPersonaPreviewMapper.toEntity(data.data)
      conflict.value = null
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      const problem = getApiProblem(err)

      // Противоречие ответов — не поломка: показываем его у полей, предыдущая картина остаётся
      if (problem && CONFLICT_CODES.includes(problem.code)) {
        conflict.value = { message: problem.detail, fields: getConflictFields(problem.code, problem) }

        return
      }

      console.error('Sandbox persona preview failed:', err)
      error.value = true
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  const loadPreviewDebounced = debounce(loadPreview, PREVIEW_DEBOUNCE)

  function onAnswersChange() {
    if (toValue(isEnabled)) loadPreviewDebounced()
  }

  watch([() => toValue(form), locale, () => toValue(isEnabled)], onAnswersChange, { deep: true, immediate: true })

  onBeforeUnmount(() => loadPreviewDebounced.cancel())

  return { preview, conflict, isLoading, error, loadPreview }
}
