import { computed, ref, toValue } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { getSessionToken, useApiFetch } from '@/app/composables/useApiFetch'
import { authService } from '@/app/services/auth/auth.service'
import { CompanyAccessMapper } from '@/app/mappers/company-access.mapper'
import type { MeInterface } from '@/app/types/company/company-access-interface'
import type { Nullable } from '@/app/types/nullable'

// Права общие для layout и страниц кабинета: layout перечитывает их при входе и смене компании, страницы берут готовые
const me = ref<Nullable<MeInterface>>(null)
const isLoading = ref(false)
const error = ref(false)

let pendingLoad: Nullable<Promise<void>> = null
// Чьи права сейчас в памяти: после входа другим человеком прежние права не показываем
let loadedToken: Nullable<string> = null

/**
 * Права текущего человека в компании из GET v1/me. Участник ООО без доступа в интернет-банк
 * (`can.view = false`, `can.approve = true`) видит в кабинете только голосование.
 */
export function useCompanyAccess(inn: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()

  const company = computed(() => me.value?.companies.find((item) => item.inn === toValue(inn)) ?? null)
  const isVotesOnly = computed(() => Boolean(company.value && !company.value.canView && company.value.canApprove))

  async function requestAccess() {
    const token = getSessionToken()

    if (token !== loadedToken) {
      me.value = null
    }

    isLoading.value = true
    error.value = false

    try {
      const { data } = await authService.fetchMe($fetch)

      me.value = CompanyAccessMapper.toMe(data.data)
      loadedToken = token
    } catch (err: unknown) {
      console.error('Company access loading failed:', err)
      error.value = true
    } finally {
      isLoading.value = false
    }
  }

  // Одновременные вызовы (layout и обновление по языку) склеиваем в один запрос
  function loadAccess() {
    pendingLoad ??= requestAccess().finally(() => {
      pendingLoad = null
    })

    return pendingLoad
  }

  return { me, company, isVotesOnly, isLoading, error, loadAccess }
}
