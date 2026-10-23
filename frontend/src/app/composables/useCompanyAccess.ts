import { computed, ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { authService } from '@/app/services/auth/auth.service'
import { CompanyAccessMapper } from '@/app/mappers/company-access.mapper'
import type { MeInterface } from '@/app/types/company/company-access-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * Права текущего человека в компании из GET v1/me. Участник ООО без доступа в интернет-банк
 * (`can.view = false`, `can.approve = true`) видит в кабинете только голосование.
 */
export function useCompanyAccess(inn: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()

  const me = ref<Nullable<MeInterface>>(null)
  const isLoading = ref(false)
  const error = ref(false)

  const company = computed(() => me.value?.companies.find((item) => item.inn === toValue(inn)) ?? null)
  const isVotesOnly = computed(() => Boolean(company.value && !company.value.canView && company.value.canApprove))

  async function loadAccess() {
    if (isLoading.value) return

    isLoading.value = true
    error.value = false

    try {
      const { data } = await authService.fetchMe($fetch)

      me.value = CompanyAccessMapper.toMe(data.data)
    } catch (err: unknown) {
      console.error('Company access loading failed:', err)
      error.value = true
    } finally {
      isLoading.value = false
    }
  }

  watch(() => toValue(inn), loadAccess, { immediate: true })

  return { me, company, isVotesOnly, isLoading, error, loadAccess }
}
