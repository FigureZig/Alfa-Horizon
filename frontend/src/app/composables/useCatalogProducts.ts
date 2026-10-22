import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { catalogService } from '@/app/services/catalog/catalog.service'
import { CatalogProductMapper } from '@/app/mappers/catalog-product.mapper'
import type { AppLocale } from '@/app/i18n'
import type { CatalogProductInterface } from '@/app/types/catalog/catalog-product-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * Продукты витрины: названия, границы суммы и срока, цели. Грузятся один раз, при смене языка — заново.
 */
export function useCatalogProducts() {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const products = ref<CatalogProductInterface[]>([])
  const keyRate = ref<Nullable<number>>(null)
  const isLoading = ref(false)
  const error = ref(false)

  async function loadProducts() {
    if (isLoading.value) return

    isLoading.value = true
    error.value = false

    try {
      const { data } = await catalogService.fetchProducts($fetch, locale.value as AppLocale)

      products.value = data.data.products.map((product) => CatalogProductMapper.toEntity(product))
      keyRate.value = data.data.key_rate.value
    } catch (err: unknown) {
      console.error('Catalog products loading failed:', err)
      error.value = !products.value.length
    } finally {
      isLoading.value = false
    }
  }

  watch(locale, loadProducts, { immediate: true })

  return { products, keyRate, isLoading, error, loadProducts }
}
