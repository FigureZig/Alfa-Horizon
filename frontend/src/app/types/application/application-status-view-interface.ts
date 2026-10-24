import type { RouteLocationRaw } from 'vue-router'
import type { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import type { ApplicationStatusToneEnum } from '@/app/types/application/application-status-tone-enum'
import type { Nullable } from '@/app/types/nullable'

// Главная кнопка шапки: команда заявки (только из available_actions) или переход
export interface ApplicationStatusActionInterface {
  label: string
  command: Nullable<ApplicationActionEnum>
  to: Nullable<RouteLocationRaw>
}

// Шапка заявки для того, кто смотрит: что происходит для меня, кто действует, сколько осталось
export interface ApplicationStatusViewInterface {
  tone: ApplicationStatusToneEnum
  icon: string
  title: string
  subtitle: string
  // Что сделать, чтобы получить больше: «Банк даст все 10 млн ₽ под 21,7 %, если перевести обороты в банк»
  hint: string
  // «Осталось 5 дней», «Срок истекает сегодня»
  deadline: string
  isDeadlineUrgent: boolean
  primary: Nullable<ApplicationStatusActionInterface>
  secondary: Nullable<ApplicationStatusActionInterface>
  // Подшаг на шаге «Решение»: «голосование участников», «у специалиста»
  substep: string
}
