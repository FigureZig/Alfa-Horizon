<script setup lang="ts">
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {dashboardService} from '@/app/services/dashboard/dashboard.service'
import {DashboardMapper} from '@/app/mappers/dashboard.mapper'
import FinanceStatCard from '@/app/features/dashboard/components/FinanceStatCard.vue'
import CashFlowChart from '@/app/features/dashboard/components/CashFlowChart.vue'
import AiRecommendationCard from '@/app/features/dashboard/components/AiRecommendationCard.vue'
import RecentTransactions from '@/app/features/dashboard/components/RecentTransactions.vue'
import {DashboardStatisticInterface} from "@/app/types/dashboard/dashboard-statistic-interface.ts";
import { useApiFetch } from '@/app/composables/useApiFetch';
import {Nullable} from "@/app/types/nullable.ts";
import { useToast } from 'primevue/usetoast'
import Skeleton from 'primevue/skeleton'

const {t, locale} = useI18n()

const $fetch = useApiFetch()
const toast = useToast()

const dashboard = ref<Nullable<DashboardStatisticInterface>>(null)
const isLoading = ref(false)
const error = ref(false)

async function onLoading() {
  if (isLoading.value) return

  isLoading.value = true
  error.value = false

  try {
    const { data } = await dashboardService.fetchDashboard($fetch)

    dashboard.value = DashboardMapper.toEntity(data.data)
  } catch (err: unknown) {
    console.error('Dashboard loading failed:', err)
    error.value = true

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: t('toast.dashboardLoadError'),
      life: 4000,
    })
  } finally {
    isLoading.value = false
  }
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat(locale.value, {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(value)
}

const stats = computed(() => {
  if (!dashboard.value) return []

  return [
    {
      title: t('dashboard.balance'),
      value: formatCurrency(dashboard.value.balance),
      icon: 'pi pi-wallet',
      description: t('dashboard.balanceDescription'),
    },
    {
      title: t('dashboard.income'),
      value: formatCurrency(dashboard.value.income),
      icon: 'pi pi-arrow-up-right',
      description: t('dashboard.incomeDescription'),
    },
    {
      title: t('dashboard.expenses'),
      value: formatCurrency(dashboard.value.expenses),
      icon: 'pi pi-arrow-down-left',
      description: t('dashboard.expensesDescription'),
    },
    {
      title: t('dashboard.activeCredits'),
      value: String(dashboard.value.activeCredits),
      icon: 'pi pi-credit-card',
      description: t('dashboard.activeCreditsDescription'),
    },
  ]
})

onMounted(onLoading)
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <div>
      <h1
        class="text-2xl font-bold tracking-tight text-fino-text sm:text-3xl"
      >
        {{ t('dashboard.title') }}
      </h1>

      <p class="mt-2 text-sm text-fino-text-muted">
        {{ t('dashboard.description') }}
      </p>
    </div>

    <!-- Финансовая статистика -->
    <!-- Финансовая статистика -->
    <section :aria-label="t('dashboard.overview')">
      <!-- Скелетоны при загрузке -->
      <div
        v-if="isLoading"
        class="grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-4"
        aria-busy="true"
      >
        <div
          v-for="index in 4"
          :key="index"
          class="rounded-3xl border border-fino-border bg-fino-surface p-5 sm:p-6"
        >
          <div class="flex items-start justify-between gap-4">
            <Skeleton
              width="55%"
              height="0.875rem"
            />

            <Skeleton
              shape="circle"
              size="2.5rem"
            />
          </div>

          <Skeleton
            width="75%"
            height="2rem"
            class="mt-6"
          />

          <Skeleton
            width="60%"
            height="0.75rem"
            class="mt-4"
          />
        </div>
      </div>

      <!-- Ошибка загрузки -->
      <div
        v-else-if="error"
        class="rounded-3xl border border-fino-border bg-fino-surface p-6"
      >
        <div class="flex items-start gap-3">
          <i
            class="pi pi-exclamation-circle mt-0.5 text-xl text-primary"
            aria-hidden="true"
          />

          <div>
            <p class="text-sm font-medium text-fino-text">
              {{ t('dashboard.loadError') }}
            </p>

            <button
              type="button"
              class="mt-3 cursor-pointer text-sm font-semibold text-primary transition-opacity hover:opacity-80"
              @click="onLoading"
            >
              <i
                class="pi pi-refresh mr-1"
                aria-hidden="true"
              />
              {{ t('dashboard.retry') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Загруженные карточки -->
      <div
        v-else-if="dashboard"
        class="grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-4"
      >
        <FinanceStatCard
          v-for="stat in stats"
          :key="stat.icon"
          :title="stat.title"
          :value="stat.value"
          :icon="stat.icon"
          :description="stat.description"
        />
      </div>
    </section>

    <!-- График и AI-рекомендации -->
    <div class="grid min-w-0 grid-cols-1 gap-4 2xl:grid-cols-3">
      <div class="min-w-0 2xl:col-span-2">
        <CashFlowChart />
      </div>

      <AiRecommendationCard />
    </div>

    <!-- Последние операции -->
    <RecentTransactions />
  </div>
</template>