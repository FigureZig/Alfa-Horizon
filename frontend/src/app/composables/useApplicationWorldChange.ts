import { computed, toValue } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { ApplicationEventInterface } from '@/app/types/application/application-event-interface'
import type { ApplicationWorldChangeInterface } from '@/app/types/application/application-world-change-interface'
import type { Nullable } from '@/app/types/nullable'

const STATUS_CHANGED = 'application.status_changed'
// Пересмотр по событию реестра бэкенд записывает от имени системы, а не воркера или движка
const SYSTEM_ACTOR = 'system'

// Причины пересмотра в тексте бэкенда → понятная клиенту формулировка без названий реестров
const REASON_KEYS: Record<string, string> = {
  'в ФНС появилась недоимка — пересмотр': 'taxDebtAppeared',
  'недоимка погашена — пересмотр': 'taxDebtPaid',
  'начато банкротство — пересмотр': 'bankruptcy',
  'в ЕГРЮЛ отметка о недостоверности сведений — пересмотр': 'unreliable',
  'компания в ликвидации — пересмотр': 'liquidation',
  'в ЕГРЮЛ новый руководитель — подпись остановлена, полномочия перепроверяются': 'directorChanged',
  'доверенность отозвана в реестре МЧД — подпись по ней остановлена': 'poaRevoked',
  'в ЕИС новый госконтракт — данные компании обновлены': 'contractSigned',
  'компанию изменили в конструкторе': 'builderChanged',
}

/**
 * Что изменилось в мире (реестрах) и заставило банк пересмотреть заявку: для плашки на странице заявки и для истории.
 */
export function useApplicationWorldChange(events: MaybeRefOrGetter<ApplicationEventInterface[]>) {
  const { t } = useI18n({ useScope: 'global' })

  function isWorldChange(event: ApplicationEventInterface): boolean {
    return event.type === STATUS_CHANGED
      && event.actor === SYSTEM_ACTOR
      && event.payload.to === ApplicationDetailStatusEnum.Checking
  }

  function getReasonKey(event: ApplicationEventInterface): string {
    return REASON_KEYS[String(event.payload.reason ?? '')] ?? 'default'
  }

  // Последний пересмотр по событию реестра
  const lastChange = computed<Nullable<ApplicationWorldChangeInterface>>(() => {
    const event = [...toValue(events)].reverse().find(isWorldChange)

    if (!event) return null

    return {
      at: event.at,
      reasonKey: getReasonKey(event),
      isSignatureReset: event.payload.from === ApplicationDetailStatusEnum.Signing,
    }
  })

  function describeChange(event: ApplicationEventInterface): string {
    return t(`application.worldChange.reason.${getReasonKey(event)}`)
  }

  return { lastChange, isWorldChange, describeChange }
}
