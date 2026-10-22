import type { SandboxFaultModeEnum } from '@/app/types/sandbox/sandbox-fault-mode-enum'
import type { Nullable } from '@/app/types/nullable'

export interface SandboxClockInterface {
  offsetSeconds: number
  now: string
  today: string
}

export interface SandboxFaultInterface {
  id: string
  source: string
  mode: SandboxFaultModeEnum
  inn: Nullable<string>
}
