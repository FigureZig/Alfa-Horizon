import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { isNotFoundError, useApiFetch } from '@/app/composables/useApiFetch'
import { companyProductsService } from '@/app/services/company/company-products.service'
import { CompanyOffersMapper } from '@/app/mappers/company-offers.mapper'
import { CreditProductMapper } from '@/app/mappers/credit-product.mapper'
import type { AppLocale } from '@/app/i18n'
import type { CompanyBlockerInterface } from '@/app/types/company/company-blocker-interface'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'

/**
 * Предодобренные продукты (K2) по ИНН. Если предложений нет, дополнительно узнаём, что мешает компании.
 */
export function useCompanyProducts(inn: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()
  const toast = useToast()
  const { t, locale } = useI18n({ useScope: 'global' })

  const products = ref<CreditProductInterface[]>([])
  const isProductsLoading = ref(false)
  const productsError = ref(false)
  const blockers = ref<CompanyBlockerInterface[]>([])

  // Номер последнего запроса: ответы по прежнему ИНН или языку отбрасываем
  let lastRequestId = 0

  // Причина пустого «Предодобрено»: без неё клиент видит пустоту, а не «что сделать». Ошибка здесь не мешает странице
  async function loadBlockers(requestId: number) {
    blockers.value = []

    if (products.value.length) return

    try {
      const { data } = await companyProductsService.fetchOffers($fetch, toValue(inn), locale.value as AppLocale)

      if (requestId !== lastRequestId) return

      blockers.value = CompanyOffersMapper.toBlockers(data.data)
    } catch (err: unknown) {
      console.error('Company blockers loading failed:', err)
    }
  }

  async function loadProducts() {
    const requestId = ++lastRequestId

    isProductsLoading.value = true
    productsError.value = false

    try {
      const { data } = await companyProductsService.fetchProducts(
        $fetch,
        toValue(inn),
        locale.value as AppLocale,
      )

      if (requestId !== lastRequestId) return

      products.value = data.data.map((product) => CreditProductMapper.toEntity(product))

      await loadBlockers(requestId)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Credit products loading failed:', err)
      products.value = []

      if (isNotFoundError(err)) return

      productsError.value = true

      toast.add({
        severity: 'error',
        summary: t('toast.error'),
        detail: t('toast.creditProductsLoadError'),
        life: 4000,
      })
    } finally {
      if (requestId === lastRequestId) {
        isProductsLoading.value = false
      }
    }
  }

  function onInnChange() {
    // Продукты прежней компании убираем сразу, не дожидаясь ответа
    products.value = []
    blockers.value = []
    loadProducts()
  }

  watch(() => toValue(inn), onInnChange, { immediate: true })
  watch(locale, loadProducts)

  return {
    products,
    isProductsLoading,
    productsError,
    blockers,
    loadProducts,
  }
}
