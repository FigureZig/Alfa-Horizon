import type { SandboxEventTypeEnum } from '@/app/types/sandbox/sandbox-event-type-enum'
import type { SandboxFaultModeEnum } from '@/app/types/sandbox/sandbox-fault-mode-enum'
import type { Nullable } from '@/app/types/nullable'

/** Часы мира: GET и POST v1/sandbox/clock. `today` — дата мира, `now` — момент с учётом сдвига. */
export interface SandboxClockDto {
  offset_s: number
  now: string
  today: string
}

/** Тело POST v1/sandbox/clock: сдвинуть часы вперёд или вернуть к реальному времени. */
export interface SandboxClockAdvanceDto {
  advance_s?: number
  advance_days?: number
  reset?: boolean
}

/** Отказ источника: GET и POST v1/sandbox/faults. Без `inn` отказ действует для всех компаний. */
export interface SandboxFaultDto {
  id: string
  source: string
  mode: SandboxFaultModeEnum
  inn: Nullable<string>
}

export interface SandboxFaultCreateDto {
  source: string
  mode: SandboxFaultModeEnum
  inn?: string
}

/** Тело POST v1/sandbox/events: `amount` — недоимка или цена контракта, только для двух типов событий. */
export interface SandboxEventCreateDto {
  type: SandboxEventTypeEnum
  inn: string
  amount?: number
}

/** Ответ POST v1/sandbox/worker/{pause|resume}. */
export interface SandboxWorkerDto {
  paused: boolean
}
