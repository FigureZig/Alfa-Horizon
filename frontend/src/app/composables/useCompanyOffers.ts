import { onBeforeUnmount, ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import debounce from 'lodash-es/debounce'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { companyProductsService } from '@/app/services/company/company-products.service'
import type { CompanyOffersParams } from '@/app/services/company/company-products.service'
import { CompanyOffersMapper } from '@/app/mappers/company-offers.mapper'
import type { AppLocale } from '@/app/i18n'
import type { CompanyOffersInterface } from '@/app/types/company/company-offers-interface'
import type { Nullable } from '@/app/types/nullable'

const OFFERS_DEBOUNCE = 400

/**
 * Подбор от задачи: все продукты компании с личными условиями под цель, сумму и срок.
 * Пересчитывается при смене параметров; последний удачный результат остаётся на экране, пока считается новый.
 */
export function useCompanyOffers(inn: MaybeRefOrGetter<string>, params: MaybeRefOrGetter<CompanyOffersParams>) {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const offers = ref<Nullable<CompanyOffersInterface>>(null)
  const isLoading = ref(false)
  const error = ref(false)

  // Номер последнего запроса: ответы по прежним параметрам отбрасываем
  let lastRequestId = 0

  async function loadOffers() {
    const requestId = ++lastRequestId

    isLoading.value = true
    error.value = false

    try {
      const { data } = await companyProductsService.fetchOffers(
        $fetch,
        toValue(inn),
        locale.value as AppLocale,
        toValue(params),
      )

      if (requestId !== lastRequestId) return

      offers.value = CompanyOffersMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Company offers loading failed:', err)
      error.value = !offers.value
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  const loadOffersDebounced = debounce(loadOffers, OFFERS_DEBOUNCE)

  function onInnChange() {
    // Подбор прежней компании убираем сразу, не дожидаясь ответа
    offers.value = null
    loadOffers()
  }

  watch(() => toValue(inn), onInnChange, { immediate: true })
  watch([() => toValue(params), locale], loadOffersDebounced, { deep: true })

  onBeforeUnmount(() => loadOffersDebounced.cancel())

  return { offers, isLoading, error, loadOffers }
}
