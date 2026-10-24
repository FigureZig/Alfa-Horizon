<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { CreditScoreClassInterface } from '@/app/types/company/credit-score-interface'

// Шкала балльной карты из политики банка (policy/*.yaml → scorecard.min / max)
const SCALE_MIN = 300
const SCALE_MAX = 900

// Чем выше класс, тем «заряженнее» цвет шкалы
const CLASS_STROKES: Record<RiskClassEnum, string> = {
  [RiskClassEnum.A]: 'var(--fino-lime)',
  [RiskClassEnum.B]: 'var(--fino-lime)',
  [RiskClassEnum.C]: 'var(--fino-amber)',
  [RiskClassEnum.D]: 'var(--p-primary-color)',
}

// Дуга-полукруг: центр (120, 120), радиус 100; длина пути нормирована к 100 — доля заполнения в процентах
const ARC_PATH = 'M 20 120 A 100 100 0 0 1 220 120'
const CENTER = 120
const RADIUS = 100

const props = defineProps<{
  score: number
  riskClass: RiskClassEnum
  classes: CreditScoreClassInterface[]
}>()

const { t } = useI18n({ useScope: 'global' })

function toPercent(value: number): number {
  const clamped = Math.min(Math.max(value, SCALE_MIN), SCALE_MAX)

  return ((clamped - SCALE_MIN) / (SCALE_MAX - SCALE_MIN)) * 100
}

// Шкала стартует с нуля и «заряжается» до балла после появления на экране
const isCharged = ref(false)

const percent = computed(() => (isCharged.value ? toPercent(props.score) : 0))
const stroke = computed(() => CLASS_STROKES[props.riskClass])
const needleAngle = computed(() => percent.value * 1.8 - 90)

// Засечки на границах классов и подписи классов посередине своего участка
const ticks = computed(() =>
  props.classes
    .filter((item) => item.min > SCALE_MIN)
    .map((item) => {
      const angle = Math.PI * (1 - toPercent(item.min) / 100)

      return {
        key: item.riskClass,
        x1: CENTER + (RADIUS - 14) * Math.cos(angle),
        y1: CENTER - (RADIUS - 14) * Math.sin(angle),
        x2: CENTER + (RADIUS + 14) * Math.cos(angle),
        y2: CENTER - (RADIUS + 14) * Math.sin(angle),
      }
    }),
)

const classLabels = computed(() => {
  const sorted = [...props.classes].sort((first, second) => first.min - second.min)

  return sorted.map((item, index) => {
    const from = Math.max(item.min, SCALE_MIN)
    const to = sorted[index + 1]?.min ?? SCALE_MAX
    const angle = Math.PI * (1 - toPercent((from + to) / 2) / 100)

    return {
      key: item.riskClass,
      x: CENTER + (RADIUS - 30) * Math.cos(angle),
      y: CENTER - (RADIUS - 30) * Math.sin(angle) + 4,
      isCurrent: item.riskClass === props.riskClass,
    }
  })
})

onMounted(() => {
  requestAnimationFrame(() => {
    isCharged.value = true
  })
})
</script>

<template>
  <figure
    class="relative mx-auto w-full max-w-72"
    :aria-label="t('credits.score.gaugeLabel', { score, riskClass })"
  >
    <svg
      viewBox="0 0 240 132"
      class="w-full overflow-visible"
      aria-hidden="true"
    >
      <!-- Корпус шкалы: чёрная обводка и пустая дорожка -->
      <path
        :d="ARC_PATH"
        fill="none"
        stroke="var(--fino-line)"
        stroke-width="24"
        stroke-linecap="round"
      />
      <path
        :d="ARC_PATH"
        fill="none"
        stroke="var(--fino-surface-secondary)"
        stroke-width="18"
        stroke-linecap="round"
      />

      <!-- Заряд: до текущего балла, пружиной -->
      <path
        :d="ARC_PATH"
        fill="none"
        :stroke="stroke"
        stroke-width="18"
        stroke-linecap="round"
        pathLength="100"
        :stroke-dasharray="`${percent} 100`"
        class="transition-[stroke-dasharray] duration-1000 ease-[cubic-bezier(0.2,1.2,0.4,1)] motion-reduce:transition-none"
      />

      <line
        v-for="tick in ticks"
        :key="tick.key"
        :x1="tick.x1"
        :y1="tick.y1"
        :x2="tick.x2"
        :y2="tick.y2"
        stroke="var(--fino-line)"
        stroke-width="2.5"
      />

      <text
        v-for="label in classLabels"
        :key="label.key"
        :x="label.x"
        :y="label.y"
        text-anchor="middle"
        class="font-mono text-[11px] font-bold"
        :fill="label.isCurrent ? 'var(--fino-text)' : 'var(--fino-text-muted)'"
      >
        {{ label.key }}
      </text>

      <!-- Стрелка: доезжает до балла с лёгким перелётом -->
      <g
        class="transition-transform duration-1000 ease-[cubic-bezier(0.2,1.6,0.4,1)] motion-reduce:transition-none"
        :style="{ transform: `rotate(${needleAngle}deg)`, transformOrigin: '120px 120px' }"
      >
        <line
          x1="120"
          y1="120"
          x2="120"
          y2="40"
          stroke="var(--fino-line)"
          stroke-width="5"
          stroke-linecap="round"
        />
      </g>
      <circle
        cx="120"
        cy="120"
        r="10"
        fill="var(--p-primary-color)"
        stroke="var(--fino-line)"
        stroke-width="3"
      />
    </svg>

    <figcaption class="mt-1 flex items-end justify-center gap-3">
      <span class="font-display text-5xl font-black leading-none tracking-tight text-fino-text tabular-nums">
        {{ score }}
      </span>

      <span
        class="mb-1 rounded-lg border-2 border-fino-line px-2 py-0.5 font-mono text-xs font-bold"
        :style="{ backgroundColor: stroke }"
        :class="riskClass === RiskClassEnum.D ? 'text-white' : 'text-[#111]'"
      >
        {{ t('credits.score.riskClass', { riskClass }) }}
      </span>
    </figcaption>
  </figure>
</template>
