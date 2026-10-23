import type { ApplicationEventDto } from '@/app/types/application/application-event-dto'
import type { ApplicationEventInterface } from '@/app/types/application/application-event-interface'

export class ApplicationEventMapper {
  static toEntity(data: ApplicationEventDto): ApplicationEventInterface {
    if (!data) {
      throw new Error('Application event data is required')
    }

    return {
      id: data.id,
      at: data.at,
      type: data.type,
      actor: data.actor,
      payload: data.payload,
      author: data.by
        ? { kind: data.by.kind, name: data.by.name, caption: data.by.title ?? data.by.detail ?? data.by.role ?? null }
        : null,
    }
  }
}
