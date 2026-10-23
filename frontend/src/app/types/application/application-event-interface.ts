import type { Nullable } from '@/app/types/nullable'

export interface ApplicationEventAuthorInterface {
  kind: 'client' | 'bank' | 'system'
  name: string
  // «Кредитный специалист», «Генеральный директор»: должность или пояснение
  caption: Nullable<string>
}

export interface ApplicationEventInterface {
  id: number
  at: string
  type: string
  actor: string
  payload: Record<string, unknown>
  author: Nullable<ApplicationEventAuthorInterface>
}
