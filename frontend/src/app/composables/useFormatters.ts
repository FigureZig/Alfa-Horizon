import { useI18n } from 'vue-i18n'

// Даты из API приходят как YYYY-MM-DD: разбираем в локальное время, чтобы не съехать на сутки
function parseIsoDate(isoDate: string): Date {
  const [year, month, day] = isoDate.split('-').map(Number)

  return new Date(year, month - 1, day)
}

export function useFormatters() {
  const { locale } = useI18n({ useScope: 'global' })

  function formatCurrency(value: number, currency: string, isCompact = false): string {
    return new Intl.NumberFormat(locale.value, {
      style: 'currency',
      currency,
      notation: isCompact ? 'compact' : 'standard',
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

  return { formatCurrency, formatPercent, formatDate, formatDateTime, formatList }
}
