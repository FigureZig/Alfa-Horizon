<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import AppErrorState from '@/app/components/AppErrorState.vue'
import BankApplicationsTable from '@/app/features/bank/components/BankApplicationsTable.vue'
import BankApplicationsTableSkeleton from '@/app/features/bank/components/BankApplicationsTableSkeleton.vue'
import { useBankApplications } from '@/app/composables/useBankApplications'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import { BankDecidedByEnum } from '@/app/types/bank/bank-decided-by-enum'

defineProps<{
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { filter, applications, isLoading, error, loadApplications, resetFilter } = useBankApplications()

const statusOptions = computed(() =>
  Object.values(ApplicationDetailStatusEnum).map((status) => ({ value: status, label: t(`application.status.${status}`) })),
)

const decidedByOptions = computed(() => [
  { value: null, label: t('bank.applications.decidedBy.all') },
  { value: BankDecidedByEnum.Engine, label: t('bank.applications.decidedBy.engine') },
  { value: BankDecidedByEnum.Bank, label: t('bank.applications.decidedBy.bank') },
])

const isFiltered = computed(() => Boolean(filter.status || filter.decidedBy || filter.query.trim()))
const isSkeletonVisible = computed(() => isLoading.value && !applications.value.length)
const isEmpty = computed(() => !isLoading.value && !error.value && !applications.value.length)
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <div class="max-w-2xl">
      <h1 class="text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
        {{ t('bank.applications.title') }}
      </h1>

      <p class="mt-2 text-sm leading-relaxed text-fino-text-muted">
        {{ t('bank.applications.description') }}
      </p>
    </div>

    <!-- Фильтры -->
    <div class="flex flex-col gap-3 lg:flex-row lg:items-center">
      <span class="relative block lg:w-80">
        <i
          class="pi pi-search pointer-events-none absolute top-1/2 left-4 -translate-y-1/2 text-sm text-fino-text-muted"
          aria-hidden="true"
        />
        <InputText
          v-model="filter.query"
          :placeholder="t('bank.applications.search')"
          :aria-label="t('bank.applications.search')"
          class="pl-10"
          fluid
        />
      </span>

      <Select
        v-model="filter.status"
        :options="statusOptions"
        option-label="label"
        option-value="value"
        :placeholder="t('bank.applications.allStatuses')"
        show-clear
        :aria-label="t('bank.applications.columns.status')"
        class="lg:w-60"
      />

      <SelectButton
        v-model="filter.decidedBy"
        :options="decidedByOptions"
        option-label="label"
        option-value="value"
        :allow-empty="false"
        :aria-label="t('bank.applications.columns.decision')"
      />

      <!-- Пока список грузится, счётчик не показываем: «0 заявок» до загрузки выглядит как пустая база -->
      <span
        v-if="!isSkeletonVisible"
        class="whitespace-nowrap text-sm text-fino-text-muted lg:ml-auto"
      >
        {{ t('bank.applications.count', applications.length) }}
      </span>
    </div>

    <BankApplicationsTableSkeleton v-if="isSkeletonVisible" />

    <AppErrorState
      v-else-if="error"
      :message="t('bank.applications.loadError')"
      @retry="loadApplications"
    />

    <div
      v-else-if="isEmpty"
      class="flex flex-col items-center rounded-3xl border border-dashed border-fino-border bg-fino-surface px-6 py-14 text-center"
    >
      <span class="flex size-14 items-center justify-center rounded-2xl bg-fino-accent text-primary">
        <i
          class="pi pi-inbox text-2xl"
          aria-hidden="true"
        />
      </span>

      <p class="mt-4 text-base font-bold text-fino-text">
        {{ isFiltered ? t('bank.applications.emptyFiltered') : t('bank.applications.empty') }}
      </p>

      <button
        v-if="isFiltered"
        type="button"
        class="mt-3 cursor-pointer text-sm font-semibold text-primary transition-opacity hover:opacity-80"
        @click="resetFilter"
      >
        {{ t('bank.applications.resetFilters') }}
      </button>
    </div>

    <BankApplicationsTable
      v-else
      :inn="inn"
      :applications="applications"
    />
  </div>
</template>
