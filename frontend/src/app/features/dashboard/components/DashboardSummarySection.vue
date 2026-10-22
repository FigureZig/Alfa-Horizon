<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import FinanceStatCard from './FinanceStatCard.vue'
import FinanceStatCardSkeleton from './FinanceStatCardSkeleton.vue'
import { useDashboardSummary } from '@/app/composables/useDashboardSummary'

const SUMMARY_SKELETON_COUNT = 3

const props = defineProps<{
  inn: string
  // Меняется, когда данные карточек устарели: карточки обновятся тихо
  refreshKey?: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { cards, error, isVisible, isSkeletonVisible, loadSummary } = useDashboardSummary(() => props.inn, () => props.refreshKey ?? '')
</script>

<template>
  <section
    v-if="isVisible"
    :aria-label="t('dashboard.overview')"
  >
    <div
      v-if="isSkeletonVisible"
      class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
      aria-busy="true"
    >
      <FinanceStatCardSkeleton
        v-for="index in SUMMARY_SKELETON_COUNT"
        :key="index"
      />
    </div>

    <AppErrorState
      v-else-if="error"
      :message="t('dashboard.loadError')"
      @retry="loadSummary"
    />

    <div
      v-else
      class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
    >
      <FinanceStatCard
        v-for="card in cards"
        :key="card.id"
        :title="card.title"
        :value="card.value"
        :icon="card.icon"
        :description="card.description"
      />
    </div>
  </section>
</template>
