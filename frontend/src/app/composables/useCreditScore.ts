import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { isNotFoundError, useApiFetch } from '@/app/composables/useApiFetch'
import { companyScoreService } from '@/app/services/company/company-score.service'
import { CreditScoreMapper } from '@/app/mappers/credit-score.mapper'
import type { AppLocale } from '@/app/i18n'
import type { CreditScoreInterface } from '@/app/types/company/credit-score-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * K3 — кредитное здоровье до заявки: балл, класс, вклад факторов и рычаги.
 * `isUnavailable`: функция выключена на бэкенде или у ИНН нет кредитного здоровья (рабочее место банка) —
 * карточку тогда не показываем.
 */
export function useCreditScore(inn: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const creditScore = ref<Nullable<CreditScoreInterface>>(null)
  const isLoading = ref(false)
  const error = ref(false)
  const isUnavailable = ref(false)

  let lastRequestId = 0

  async function loadCreditScore() {
    const requestId = ++lastRequestId

    isLoading.value = true
    error.value = false
    isUnavailable.value = false

    try {
      const { data } = await companyScoreService.fetchScore($fetch, toValue(inn), locale.value as AppLocale)

      if (requestId !== lastRequestId) return

      creditScore.value = CreditScoreMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Credit score loading failed:', err)
      creditScore.value = null
      isUnavailable.value = isNotFoundError(err)
      error.value = !isUnavailable.value
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  function onInnChange() {
    creditScore.value = null
    loadCreditScore()
  }

  watch(() => toValue(inn), onInnChange, { immediate: true })
  watch(locale, loadCreditScore)

  return { creditScore, isLoading, error, isUnavailable, loadCreditScore }
}
