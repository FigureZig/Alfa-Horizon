import { ref } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxWorldMapper } from '@/app/mappers/sandbox-world.mapper'
import type { SandboxClockAdvanceDto, SandboxEventCreateDto, SandboxFaultCreateDto } from '@/app/types/sandbox/sandbox-world-dto'
import type { SandboxClockInterface, SandboxFaultInterface } from '@/app/types/sandbox/sandbox-world-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * Пульт мира симулятора: часы, отказы источников, пауза воркера, события реестров и сброс.
 * Команды бросают ошибку дальше — уведомление показывает панель.
 */
export function useSandboxWorld() {
  const $fetch = useApiFetch()

  const clock = ref<Nullable<SandboxClockInterface>>(null)
  const faults = ref<SandboxFaultInterface[]>([])
  // Бэкенд не отдаёт состояние воркера, только подтверждает команду: до первой команды считаем, что он работает
  const isWorkerPaused = ref(false)
  const isLoading = ref(false)
  const error = ref(false)

  async function loadWorld() {
    if (isLoading.value) return

    isLoading.value = true
    error.value = false

    try {
      const [clockResponse, faultsResponse] = await Promise.all([
        sandboxService.fetchClock($fetch),
        sandboxService.fetchFaults($fetch),
      ])

      clock.value = SandboxWorldMapper.clockToEntity(clockResponse.data.data)
      faults.value = faultsResponse.data.data.map((fault) => SandboxWorldMapper.faultToEntity(fault))
    } catch (err: unknown) {
      console.error('Sandbox world loading failed:', err)
      error.value = true
    } finally {
      isLoading.value = false
    }
  }

  async function advanceClock(payload: SandboxClockAdvanceDto) {
    const { data } = await sandboxService.advanceClock($fetch, payload)

    clock.value = SandboxWorldMapper.clockToEntity(data.data)
  }

  async function createEvent(payload: SandboxEventCreateDto) {
    await sandboxService.createEvent($fetch, payload)
  }

  async function createFault(payload: SandboxFaultCreateDto) {
    const { data } = await sandboxService.createFault($fetch, payload)

    faults.value = [...faults.value, SandboxWorldMapper.faultToEntity(data.data)]
  }

  async function deleteFault(faultId: string) {
    await sandboxService.deleteFault($fetch, faultId)

    faults.value = faults.value.filter((fault) => fault.id !== faultId)
  }

  async function toggleWorker() {
    const { data } = await sandboxService.setWorkerPaused($fetch, !isWorkerPaused.value)

    isWorkerPaused.value = data.data.paused
  }

  async function resetWorld() {
    await sandboxService.reset($fetch)

    isWorkerPaused.value = false
    await loadWorld()
  }

  return {
    clock,
    faults,
    isWorkerPaused,
    isLoading,
    error,
    loadWorld,
    advanceClock,
    createEvent,
    createFault,
    deleteFault,
    toggleWorker,
    resetWorld,
  }
}
