import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import type { AppLocale } from '@/app/i18n'

/**
 * Названия компаний по ИНН для рабочего места банка: в очереди приходит только ИНН,
 * а название знает список компаний песочницы. Не загрузился — показываем ИНН.
 */
export function useCompanyNames() {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const names = ref<Record<string, string>>({})
  const isLoading = ref(true)

  const getCompanyName = computed(() => (inn: string) => names.value[inn] ?? '')

  async function loadCompanyNames() {
    try {
      const { data } = await sandboxService.fetchPersonas($fetch, locale.value as AppLocale)
      const result: Record<string, string> = {}

      for (const persona of data.data) {
        for (const company of persona.companies ?? []) {
          result[company.inn] = company.name
        }
      }

      names.value = result
    } catch (err: unknown) {
      console.error('Company names loading failed:', err)
    } finally {
      isLoading.value = false
    }
  }

  loadCompanyNames()

  return { getCompanyName, isLoading }
}
