<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import Skeleton from 'primevue/skeleton'
import type { BankAuditInterface } from '@/app/types/bank/bank-audit-interface'
import type { Nullable } from '@/app/types/nullable'

const HASH_PREVIEW_LENGTH = 16

const props = defineProps<{
  audit: Nullable<BankAuditInterface>
  isLoading: boolean
  hasError: boolean
}>()

const emit = defineEmits<{
  recheck: []
}>()

const { t } = useI18n({ useScope: 'global' })

const isSkeletonVisible = computed(() => props.isLoading && !props.audit)
const hashPreview = computed(() => props.audit?.lastHash?.slice(0, HASH_PREVIEW_LENGTH) ?? '')

function handleRecheck() {
  emit('recheck')
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-4 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm"
    :aria-label="t('bank.audit.title')"
  >
    <div>
      <h2 class="text-sm font-semibold text-fino-text">
        {{ t('bank.audit.title') }}
      </h2>

      <p class="mt-1 text-xs text-fino-text-muted">
        {{ t('bank.audit.description') }}
      </p>
    </div>

    <div
      v-if="isSkeletonVisible"
      class="flex flex-col gap-3"
      aria-busy="true"
    >
      <Skeleton
        height="3.5rem"
        border-radius="1rem"
      />

      <Skeleton
        width="60%"
        height="0.875rem"
      />
    </div>

    <AppErrorState
      v-else-if="hasError"
      :message="t('bank.audit.loadError')"
      is-inline
      @retry="handleRecheck"
    />

    <template v-else-if="audit">
      <p
        class="flex items-center gap-3 rounded-2xl p-4 text-sm font-semibold"
        :class="audit.isIntact
          ? 'bg-green-500/10 text-green-700 dark:text-green-400'
          : 'bg-red-500/10 text-red-700 dark:text-red-400'"
        role="status"
      >
        <i
          :class="audit.isIntact ? 'pi pi-shield' : 'pi pi-exclamation-triangle'"
          class="text-xl"
          aria-hidden="true"
        />
        {{ audit.isIntact ? t('bank.audit.intact') : t('bank.audit.broken', { number: audit.brokenAt }) }}
      </p>

      <dl class="flex flex-col gap-1.5 text-sm">
        <div class="flex justify-between gap-3">
          <dt class="text-fino-text-muted">
            {{ t('bank.audit.events') }}
          </dt>
          <dd class="font-semibold text-fino-text">
            {{ audit.eventsCount }}
          </dd>
        </div>

        <div
          v-if="hashPreview"
          class="flex justify-between gap-3"
        >
          <dt class="text-fino-text-muted">
            {{ t('bank.audit.lastHash') }}
          </dt>
          <dd class="font-mono text-xs font-semibold text-fino-text">
            {{ hashPreview }}…
          </dd>
        </div>
      </dl>
    </template>

    <button
      type="button"
      class="inline-flex min-h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-xl border
             border-fino-border bg-fino-surface px-4 py-2.5 text-sm font-semibold text-fino-text
             transition-colors duration-200 hover:bg-fino-surface-hover
             disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
             focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      :disabled="isLoading"
      @click="handleRecheck"
    >
      <i
        :class="isLoading ? 'pi pi-spinner pi-spin' : 'pi pi-refresh'"
        class="text-xs"
        aria-hidden="true"
      />
      {{ t('bank.audit.recheck') }}
    </button>
  </article>
</template>
