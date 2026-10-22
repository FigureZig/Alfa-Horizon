export interface ApplicationEventInterface {
  id: number
  at: string
  type: string
  actor: string
  payload: Record<string, unknown>
}
