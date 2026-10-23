import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { bankService } from '@/app/services/bank/bank.service'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import type { AppLocale } from '@/app/i18n'
import type { Nullable } from '@/app/types/nullable'

// Названия общие для банковских страниц: переходы между очередью и досье не перечитывают реестр и список компаний
const CACHE_TTL = 60000
const cachedNames = ref<Record<string, string>>({})
let cachedAt = 0
let pendingLoad: Nullable<Promise<void>> = null

/**
 * Названия компаний по ИНН для рабочего места банка: в очереди приходит только ИНН.
 * Название берём из списка компаний, а у удалённых компаний — из реестра заявок, где оно сохранено при подаче.
 * Не нашлось — показываем ИНН.
 */
export function useCompanyNames() {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const isLoading = ref(!cachedAt)

  const getCompanyName = computed(() => (inn: string) => cachedNames.value[inn] ?? '')

  function loadCompanyNames() {
    if (Date.now() - cachedAt < CACHE_TTL) return Promise.resolve()

    pendingLoad ??= requestCompanyNames().finally(() => {
      pendingLoad = null
    })

    return pendingLoad
  }

  async function requestCompanyNames() {
    const [registry, personas] = await Promise.allSettled([
      bankService.fetchApplications($fetch, { status: null, decidedBy: null, query: '' }),
      sandboxService.fetchPersonas($fetch, locale.value as AppLocale),
    ])
    const result: Record<string, string> = {}

    // Сначала реестр заявок (имена удалённых компаний), затем актуальный список — он важнее
    if (registry.status === 'fulfilled') {
      for (const application of registry.value.data.data) {
        if (application.company_name) result[application.inn] = application.company_name
      }
    } else {
      console.error('Company names from the registry failed:', registry.reason)
    }

    if (personas.status === 'fulfilled') {
      for (const persona of personas.value.data.data) {
        for (const company of persona.companies ?? []) {
          result[company.inn] = company.name
        }
      }
    } else {
      console.error('Company names loading failed:', personas.reason)
    }

    cachedNames.value = result
    cachedAt = Date.now()
  }

  async function init() {
    await loadCompanyNames()
    isLoading.value = false
  }

  init()

  return { getCompanyName, isLoading }
}
