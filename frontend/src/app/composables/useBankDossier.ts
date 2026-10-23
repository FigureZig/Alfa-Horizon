import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { bankService } from '@/app/services/bank/bank.service'
import { BankDossierMapper } from '@/app/mappers/bank-dossier.mapper'
import type { BankDossierInterface } from '@/app/types/bank/bank-dossier-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * Досье: факты о компании и источники, откуда они взяты. Сама заявка и история приходят отдельно
 * (с живыми обновлениями), поэтому здесь только то, чего там нет. `version` меняется — досье перечитываем.
 */
export function useBankDossier(applicationId: MaybeRefOrGetter<string>, version: MaybeRefOrGetter<Nullable<string>>) {
  const $fetch = useApiFetch()

  const dossier = ref<Nullable<BankDossierInterface>>(null)
  const isLoading = ref(false)
  const error = ref(false)

  let lastRequestId = 0

  async function loadDossier() {
    const requestId = ++lastRequestId

    isLoading.value = true
    error.value = false

    try {
      const { data } = await bankService.fetchDossier($fetch, toValue(applicationId))

      if (requestId !== lastRequestId) return

      dossier.value = BankDossierMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Bank dossier loading failed:', err)
      error.value = !dossier.value
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  function onApplicationChange() {
    dossier.value = null
    loadDossier()
  }

  watch(() => toValue(applicationId), onApplicationChange, { immediate: true })
  // Версия появляется вместе с заявкой, когда досье уже грузится; перечитываем только при её смене
  function onVersionChange(_: Nullable<string>, previousVersion: Nullable<string>) {
    if (!previousVersion) return

    loadDossier()
  }

  watch(() => toValue(version), onVersionChange)

  return { dossier, isLoading, error, loadDossier }
}
