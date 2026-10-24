import { onBeforeUnmount, ref } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxWorldMapper } from '@/app/mappers/sandbox-world.mapper'
import type { Nullable } from '@/app/types/nullable'

const TICK_MS = 30_000

// Часы мира общие для всех экранов: сколько показывали при загрузке и когда мы это узнали
const worldNowAtLoad = ref<Nullable<number>>(null)
let loadedAt = 0
let pendingLoad: Nullable<Promise<void>> = null

/**
 * «Сейчас» по часам мира, а не браузера: время мира можно перемотать, и сроки считаются по нему.
 * Часы читаем один раз, дальше идём вперёд сами — раз в полминуты, этого хватает для «осталось 3 ч 40 мин».
 */
export function useWorldClock() {
  const $fetch = useApiFetch()

  const now = ref<Nullable<number>>(null)

  async function requestClock() {
    try {
      const { data } = await sandboxService.fetchClock($fetch)

      worldNowAtLoad.value = new Date(SandboxWorldMapper.clockToEntity(data.data).now).getTime()
      loadedAt = Date.now()
    } catch (err: unknown) {
      console.error('World clock loading failed:', err)
    }
  }

  function tick() {
    now.value = worldNowAtLoad.value === null ? null : worldNowAtLoad.value + (Date.now() - loadedAt)
  }

  async function loadClock() {
    pendingLoad ??= requestClock().finally(() => {
      pendingLoad = null
    })

    await pendingLoad
    tick()
  }

  const timer = setInterval(tick, TICK_MS)

  onBeforeUnmount(() => clearInterval(timer))

  loadClock()

  return { now, loadClock }
}
