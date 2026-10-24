import { readonly, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { getSessionToken, isNotFoundError, useApiFetch } from '@/app/composables/useApiFetch'
import { demoPersonaService } from '@/app/services/demo-persona/demo-persona.service'
import { DemoPersonaMapper } from '@/app/mappers/demo-persona.mapper'
import type { AppLocale } from '@/app/i18n'
import type { DemoPersonaInterface } from '@/app/types/demo-persona/demo-persona-interface'
import type { Nullable } from '@/app/types/nullable'

// Состояние общее для шапки, layout и страниц кабинета
const demoPersona = ref<Nullable<DemoPersonaInterface>>(null)
const isLoading = ref(false)
const error = ref(false)

// Номер последнего запроса: ответы устаревших запросов (другая персона или язык) отбрасываем
let lastRequestId = 0

// Layout и страница просят одну и ту же персону одновременно — второй запрос не нужен
let pendingKey = ''
let pendingRequest: Nullable<Promise<void>> = null
// Под чьим токеном загружена персона: после входа другим человеком прежнего в шапке не показываем
let loadedToken: Nullable<string> = null

function resetDemoPersona() {
  lastRequestId++
  demoPersona.value = null
  isLoading.value = false
  error.value = false
}

export function useDemoPersona() {
  const $fetch = useApiFetch()
  const toast = useToast()
  const router = useRouter()
  const { t, locale } = useI18n({ useScope: 'global' })

  function loadDemoPersona(inn: string) {
    const key = `${inn}:${locale.value}:${getSessionToken() ?? ''}`

    if (pendingRequest && pendingKey === key) return pendingRequest

    pendingKey = key
    pendingRequest = requestDemoPersona(inn).finally(() => {
      if (pendingKey === key) pendingRequest = null
    })

    return pendingRequest
  }

  async function requestDemoPersona(inn: string) {
    const requestId = ++lastRequestId
    const token = getSessionToken()

    // Не показываем данные предыдущей персоны, пока грузится новая: другая компания или другой человек
    if (demoPersona.value?.inn !== inn || token !== loadedToken) {
      demoPersona.value = null
    }

    isLoading.value = true
    error.value = false

    try {
      const { data } = await demoPersonaService.fetchDemoPersona(
        $fetch,
        inn,
        locale.value as AppLocale,
      )

      if (requestId !== lastRequestId) return

      demoPersona.value = DemoPersonaMapper.toEntity(data.data)
      loadedToken = token
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Demo persona loading failed:', err)

      if (isNotFoundError(err)) {
        toast.add({
          severity: 'error',
          summary: t('toast.error'),
          detail: t('toast.demoPersonaNotFound'),
          life: 4000,
        })

        resetDemoPersona()
        await router.replace({ name: 'login' })

        return
      }

      error.value = true

      toast.add({
        severity: 'error',
        summary: t('toast.error'),
        detail: t('toast.demoPersonaLoadError'),
        life: 4000,
      })
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  return {
    demoPersona: readonly(demoPersona),
    isLoading: readonly(isLoading),
    error: readonly(error),
    loadDemoPersona,
    resetDemoPersona,
  }
}
