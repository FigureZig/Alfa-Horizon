import type { SandboxClockDto, SandboxFaultDto } from '@/app/types/sandbox/sandbox-world-dto'
import type { SandboxClockInterface, SandboxFaultInterface } from '@/app/types/sandbox/sandbox-world-interface'

export class SandboxWorldMapper {
  static clockToEntity(data: SandboxClockDto): SandboxClockInterface {
    return {
      offsetSeconds: data.offset_s,
      now: data.now,
      today: data.today,
    }
  }

  static faultToEntity(data: SandboxFaultDto): SandboxFaultInterface {
    return {
      id: data.id,
      source: data.source,
      mode: data.mode,
      inn: data.inn ?? null,
    }
  }
}
