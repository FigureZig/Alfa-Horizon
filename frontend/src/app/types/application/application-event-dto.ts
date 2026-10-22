/** Запись истории заявки: GET v1/applications/{id}/events и события потока .../stream. */
export interface ApplicationEventDto {
  id: number
  at: string
  type: string
  actor: string
  payload: Record<string, unknown>
}
