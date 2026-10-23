import { useI18n } from 'vue-i18n'

const DATE_ONLY_PATTERN = /^\d{4}-\d{2}-\d{2}$/

// Дата YYYY-MM-DD — в локальное время, чтобы не съехать на сутки; дата со временем (ISO 8601) — как есть
function parseIsoDate(isoDate: string): Date {
  if (!DATE_ONLY_PATTERN.test(isoDate)) return new Date(isoDate)

  const [year, month, day] = isoDate.split('-').map(Number)

  return new Date(year, month - 1, day)
}

const MS_IN_DAY = 24 * 60 * 60 * 1000

export function useFormatters() {
  const { locale } = useI18n({ useScope: 'global' })

  function formatCurrency(value: number, currency: string, isCompact = false): string {
    return new Intl.NumberFormat(locale.value, {
      style: 'currency',
      currency,
      notation: isCompact ? 'compact' : 'standard',
      minimumFractionDigits: 0,
      maximumFractionDigits: isCompact ? 1 : 0,
    }).format(value)
  }

  function formatPercent(value: number): string {
    return new Intl.NumberFormat(locale.value, {
      style: 'percent',
      maximumFractionDigits: 2,
    }).format(value / 100)
  }

  function formatDate(isoDate: string, options: Intl.DateTimeFormatOptions): string {
    return new Intl.DateTimeFormat(locale.value, options).format(parseIsoDate(isoDate))
  }

  // Для меток времени с часами (ISO 8601 с временем)
  function formatDateTime(isoDateTime: string, options: Intl.DateTimeFormatOptions): string {
    return new Intl.DateTimeFormat(locale.value, options).format(new Date(isoDateTime))
  }

  // «ЕГРЮЛ, ФНС и счёт в банке»
  function formatList(items: string[]): string {
    return new Intl.ListFormat(locale.value, { type: 'conjunction' }).format(items)
  }

  // Длительность в секундах: «0,27 сек.», «12 сек.», «15 мин.»
  function formatDuration(seconds: number): string {
    const isMinutes = seconds >= 60

    return new Intl.NumberFormat(locale.value, {
      style: 'unit',
      unit: isMinutes ? 'minute' : 'second',
      unitDisplay: 'short',
      maximumFractionDigits: isMinutes || seconds >= 10 ? 0 : 2,
    }).format(isMinutes ? seconds / 60 : seconds)
  }

  // Сколько дней осталось до срока: по датам, а не по времени суток («оферта на 10 дней» — «осталось 10 дней»);
  // «сегодня» — дата мира из API (YYYY-MM-DD), а не часы браузера
  function getDaysLeft(dueIsoDateTime: string, today: string): number {
    const due = new Date(dueIsoDateTime)
    const dueDay = new Date(due.getFullYear(), due.getMonth(), due.getDate())

    return Math.max(Math.round((dueDay.getTime() - parseIsoDate(today).getTime()) / MS_IN_DAY), 0)
  }

  return { getDaysLeft, formatCurrency, formatPercent, formatDate, formatDateTime, formatList, formatDuration }
}
