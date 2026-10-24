import { computed, ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { isNotFoundError, useApiFetch } from '@/app/composables/useApiFetch'
import { useFormatters } from '@/app/composables/useFormatters'
import { dashboardService } from '@/app/services/dashboard/dashboard.service'
import { DashboardMapper } from '@/app/mappers/dashboard.mapper'
import { DashboardSummaryCardTypeEnum } from '@/app/types/dashboard/dashboard-summary-card-type-enum'
import type { AppLocale } from '@/app/i18n'
import type { DashboardSummaryCardInterface } from '@/app/types/dashboard/dashboard-summary-card-interface'

const DEFAULT_CARD_ICON = 'pi pi-chart-line'

const SUMMARY_CARD_ICONS: Record<DashboardSummaryCardTypeEnum, string> = {
  [DashboardSummaryCardTypeEnum.Balance]: 'pi pi-wallet',
  [DashboardSummaryCardTypeEnum.Outflow]: 'pi pi-arrow-up-right',
  [DashboardSummaryCardTypeEnum.Inflow]: 'pi pi-arrow-down-left',
}

/**
 * Карточки сводки по ИНН: количество, заголовки и суммы определяет бэкенд.
 * У компании это остаток и платежи до даты разрыва, у рабочего места банка — очередь, второй ключ и выдачи.
 */
export function useDashboardSummary(inn: MaybeRefOrGetter<string>, refreshKey?: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()
  const toast = useToast()
  const { t, locale } = useI18n({ useScope: 'global' })
  const { formatCurrency } = useFormatters()

  const summaryCards = ref<DashboardSummaryCardInterface[]>([])
  const isLoading = ref(false)
  const error = ref(false)

  // Номер последнего запроса: ответ по предыдущей персоне не должен перезаписать текущую
  let lastRequestId = 0

  // Скелетоны только при первой загрузке: при смене языка карточки остаются на месте
  const isSkeletonVisible = computed(() => isLoading.value && !summaryCards.value.length)

  // Пустой массив от бэкенда — блок карточек не показываем вовсе
  const isVisible = computed(() => isLoading.value || error.value || summaryCards.value.length > 0)

  const cards = computed(() =>
    summaryCards.value.map((card) => ({
      id: card.id,
      type: card.type,
      title: card.title,
      value: formatCurrency(card.amount, card.currency),
      icon: SUMMARY_CARD_ICONS[card.type] ?? DEFAULT_CARD_ICON,
      description: card.description,
    })),
  )

  async function loadSummary() {
    const requestId = ++lastRequestId

    isLoading.value = true
    error.value = false

    try {
      const { data } = await dashboardService.fetchSummary($fetch, toValue(inn), locale.value as AppLocale)

      if (requestId !== lastRequestId) return

      summaryCards.value = data.data.map((card) => DashboardMapper.toEntity(card))
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Dashboard summary loading failed:', err)
      summaryCards.value = []

      // Несуществующую персону обрабатывает загрузка её профиля (уведомление и возврат в /sandbox)
      if (isNotFoundError(err)) return

      error.value = true

      toast.add({
        severity: 'error',
        summary: t('toast.error'),
        detail: t('toast.dashboardLoadError'),
        life: 4000,
      })
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  function onInnChange() {
    // Карточки другой персоны сразу убираем, при смене языка оставляем до ответа
    summaryCards.value = []
    loadSummary()
  }

  // Пустой ключ → первый состав очереди: сводка уже загружена параллельно, повторять запрос незачем
  function onRefreshKeyChange(_key: string, previousKey: string) {
    if (!previousKey) return

    loadSummary()
  }

  watch(() => toValue(inn), onInnChange, { immediate: true })
  watch(locale, loadSummary)

  // Данные за карточками изменились (например, очередь банка): обновляем их, не сбрасывая показанное
  if (refreshKey) {
    watch(() => toValue(refreshKey), onRefreshKeyChange)
  }

  return { cards, isLoading, error, isVisible, isSkeletonVisible, loadSummary }
}
