// Смысл цвета шапки заявки: зелёный — готово, янтарный — нужно действие, красный — отказ или срок, остальное — нейтрально
export enum ApplicationStatusToneEnum {
  Neutral = 'neutral',
  Busy = 'busy',
  Action = 'action',
  Success = 'success',
  Danger = 'danger',
}
