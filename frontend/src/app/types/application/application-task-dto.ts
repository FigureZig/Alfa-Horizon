/**
 * Задача пользователя: GET v1/tasks — входящие по всем его компаниям.
 * `action: vote` — банк ждёт голос участника по крупной сделке.
 */
export interface ApplicationTaskDto {
  id: string
  type: string
  action: string
  title: string
  due_date: string
  application_id: string
  company_inn: string
  status: string
}
