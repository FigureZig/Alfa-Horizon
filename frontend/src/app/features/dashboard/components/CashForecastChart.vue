<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type {
  CashForecastPointInterface,
  CashGapInterface,
} from '@/app/types/company/cash-forecast-interface'
import type { Nullable } from '@/app/types/nullable'

// Координаты графика — проценты от области построения (viewBox 0 0 100 100)
const PADDING_X = 1.5
const PADDING_TOP = 10
// Снизу больше места: под точкой разрыва стоит подпись с суммой
const PADDING_BOTTOM = 22
const VALUE_PADDING_RATIO = 0.08

const props = defineProps<{
  points: CashForecastPointInterface[]
  cashGap: Nullable<CashGapInterface>
  currency: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatDate } = useFormatters()

const hoveredIndex = ref<Nullable<number>>(null)

const valueRange = computed(() => {
  const balances = props.points.map((point) => point.balance)
  // Ноль всегда в области графика — от него читается разрыв
  const min = Math.min(0, ...balances)
  const max = Math.max(0, ...balances)
  const padding = (max - min || 1) * VALUE_PADDING_RATIO

  return { max, top: max + padding, bottom: min - padding }
})

function getX(index: number): number {
  const lastIndex = Math.max(props.points.length - 1, 1)

  return PADDING_X + (index / lastIndex) * (100 - PADDING_X * 2)
}

function getY(value: number): number {
  const { top, bottom } = valueRange.value

  return PADDING_TOP + ((top - value) / (top - bottom)) * (100 - PADDING_TOP - PADDING_BOTTOM)
}

const coordinates = computed(() =>
  props.points.map((point, index) => ({ x: getX(index), y: getY(point.balance) })),
)

const zeroY = computed(() => getY(0))

const linePath = computed(() =>
  coordinates.value
    .map((point, index) => `${index ? 'L' : 'M'}${point.x},${point.y}`)
    .join(' '),
)

// Область между линией и нулём; клип оставляет только часть ниже нуля
const areaPath = computed(() => {
  const first = coordinates.value[0]
  const last = coordinates.value[coordinates.value.length - 1]

  if (!first || !last) return ''

  return `${linePath.value} L${last.x},${zeroY.value} L${first.x},${zeroY.value} Z`
})

const negativeClipHeight = computed(() => Math.max(100 - zeroY.value, 0))

const gapPoint = computed(() => {
  if (!props.cashGap) return null

  const index = props.points.findIndex((point) => point.date === props.cashGap?.date)

  return index >= 0 ? coordinates.value[index] : null
})

const gapLabel = computed(() =>
  props.cashGap ? formatCurrency(-props.cashGap.amount, props.currency) : '',
)

const axisLabels = computed(() => [
  { key: 'max', value: formatCurrency(valueRange.value.max, props.currency, true), y: getY(valueRange.value.max) },
  { key: 'zero', value: formatCurrency(0, props.currency, true), y: zeroY.value },
])

const dateLabels = computed(() => {
  const middleIndex = Math.floor((props.points.length - 1) / 2)

  return [0, middleIndex, props.points.length - 1]
    .filter((index) => props.points[index])
    .map((index) => ({
      key: props.points[index].date,
      value: index === 0
        ? t('cashForecast.today')
        : formatDate(props.points[index].date, { day: 'numeric', month: 'short' }),
    }))
})

const hoveredPoint = computed(() => {
  if (hoveredIndex.value === null) return null

  const point = props.points[hoveredIndex.value]
  const coordinate = coordinates.value[hoveredIndex.value]

  if (!point || !coordinate) return null

  return {
    ...coordinate,
    date: formatDate(point.date, { day: 'numeric', month: 'long' }),
    balance: formatCurrency(point.balance, props.currency),
  }
})

// Подсказка у краёв прижимается внутрь, чтобы не вылезать за карточку
const tooltipStyle = computed(() => {
  if (!hoveredPoint.value) return {}

  const { x } = hoveredPoint.value
  const shift = x < 20 ? '0%' : x > 80 ? '-100%' : '-50%'

  return { left: `${x}%`, transform: `translateX(${shift})` }
})

const chartLabel = computed(() =>
  props.cashGap
    ? `${t('cashForecast.chartLabel')}. ${gapLabel.value}`
    : t('cashForecast.chartLabel'),
)

const tableRows = computed(() =>
  props.points.map((point) => ({
    key: point.date,
    date: formatDate(point.date, { day: 'numeric', month: 'long' }),
    balance: formatCurrency(point.balance, props.currency),
  })),
)

function getPositionStyle(x: number, y: number) {
  return { left: `${x}%`, top: `${y}%` }
}

function getAxisLabelStyle(y: number) {
  return { top: `${y}%` }
}

function handlePointerMove(event: PointerEvent) {
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const ratio = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1)
  const lastIndex = props.points.length - 1

  hoveredIndex.value = Math.round(ratio * lastIndex)
}

function handlePointerLeave() {
  hoveredIndex.value = null
}
</script>

<template>
  <div class="min-w-0">
    <div class="flex gap-2">
      <!-- Ось значений -->
      <div
        class="relative w-14 shrink-0 text-right text-[11px] leading-none text-fino-text-muted"
        aria-hidden="true"
      >
        <span
          v-for="label in axisLabels"
          :key="label.key"
          class="absolute right-0 -translate-y-1/2 whitespace-nowrap"
          :style="getAxisLabelStyle(label.y)"
        >
          {{ label.value }}
        </span>
      </div>

      <!-- Область построения -->
      <div
        class="relative h-48 min-w-0 flex-1 touch-pan-y sm:h-56"
        @pointermove="handlePointerMove"
        @pointerleave="handlePointerLeave"
      >
        <svg
          class="absolute inset-0 size-full overflow-visible"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          role="img"
          :aria-label="chartLabel"
        >
          <defs>
            <clipPath id="cash-forecast-negative">
              <rect
                x="0"
                :y="zeroY"
                width="100"
                :height="negativeClipHeight"
              />
            </clipPath>
          </defs>

          <!-- Зона отрицательного остатка -->
          <path
            :d="areaPath"
            clip-path="url(#cash-forecast-negative)"
            class="fill-red-500/15 dark:fill-red-500/25"
          />

          <!-- Нулевая отметка -->
          <line
            x1="0"
            x2="100"
            :y1="zeroY"
            :y2="zeroY"
            class="stroke-fino-text-muted/60"
            stroke-width="1"
            stroke-dasharray="4 4"
            vector-effect="non-scaling-stroke"
          />

          <!-- Прогноз остатка -->
          <path
            :d="linePath"
            fill="none"
            class="stroke-blue-500 dark:stroke-blue-400"
            stroke-width="2"
            stroke-linejoin="round"
            stroke-linecap="round"
            vector-effect="non-scaling-stroke"
          />
        </svg>

        <!-- Перекрестие при наведении -->
        <div
          v-if="hoveredPoint"
          class="pointer-events-none absolute inset-y-0 w-px bg-fino-border"
          :style="getPositionStyle(hoveredPoint.x, 0)"
          aria-hidden="true"
        />

        <!-- Точка максимального разрыва -->
        <template v-if="gapPoint">
          <span
            class="pointer-events-none absolute size-3 -translate-x-1/2 -translate-y-1/2
                   rounded-full bg-red-500 ring-2 ring-fino-surface"
            :style="getPositionStyle(gapPoint.x, gapPoint.y)"
            aria-hidden="true"
          />

          <span
            class="pointer-events-none absolute -translate-x-1/2 translate-y-2.5
                   whitespace-nowrap rounded-lg bg-fino-surface px-1.5 py-0.5
                   text-xs font-semibold text-fino-text shadow-sm"
            :style="getPositionStyle(gapPoint.x, gapPoint.y)"
            aria-hidden="true"
          >
            {{ gapLabel }}
          </span>
        </template>

        <!-- Точка под курсором -->
        <span
          v-if="hoveredPoint"
          class="pointer-events-none absolute size-2.5 -translate-x-1/2 -translate-y-1/2
                 rounded-full bg-blue-500 ring-2 ring-fino-surface dark:bg-blue-400"
          :style="getPositionStyle(hoveredPoint.x, hoveredPoint.y)"
          aria-hidden="true"
        />

        <!-- Подсказка -->
        <div
          v-if="hoveredPoint"
          class="pointer-events-none absolute -top-2 z-10 whitespace-nowrap rounded-xl
                 border border-fino-border bg-fino-surface px-3 py-2 shadow-md"
          :style="tooltipStyle"
          aria-hidden="true"
        >
          <p class="text-xs text-fino-text-muted">
            {{ hoveredPoint.date }}
          </p>

          <p class="text-sm font-semibold text-fino-text">
            {{ hoveredPoint.balance }}
          </p>
        </div>
      </div>
    </div>

    <!-- Ось дат -->
    <div
      class="mt-2 flex justify-between pl-16 text-xs text-fino-text-muted"
      aria-hidden="true"
    >
      <span
        v-for="label in dateLabels"
        :key="label.key"
      >
        {{ label.value }}
      </span>
    </div>

    <!-- Табличное представление для скринридеров -->
    <table class="sr-only">
      <caption>{{ t('cashForecast.chartLabel') }}</caption>
      <thead>
        <tr>
          <th scope="col">
            {{ t('cashForecast.tableDate') }}
          </th>
          <th scope="col">
            {{ t('cashForecast.tableBalance') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in tableRows"
          :key="row.key"
        >
          <td>{{ row.date }}</td>
          <td>{{ row.balance }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
