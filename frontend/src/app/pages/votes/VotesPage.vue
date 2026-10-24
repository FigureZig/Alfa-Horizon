<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import VoteCard from '@/app/features/votes/components/VoteCard.vue'
import VoteCardSkeleton from '@/app/features/votes/components/VoteCardSkeleton.vue'
import { useCompanyAccess } from '@/app/composables/useCompanyAccess'
import { useReviewerPanel } from '@/app/composables/useReviewerPanel'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useVoteTasks } from '@/app/composables/useVoteTasks'

const VOTE_SKELETON_COUNT = 2
// Сценарий, в котором банк просит участников согласовать крупную сделку (id из /sandbox/scenarios)
const VOTE_SCENARIO_ID = 'large-deal'

const props = defineProps<{
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { demoPersona } = useDemoPersona()
const { me, company } = useCompanyAccess(() => props.inn)
const { items, isLoading, error, loadVotes } = useVoteTasks(() => props.inn)
const { openPanel } = useReviewerPanel()

function openVoteScenario() {
  openPanel(VOTE_SCENARIO_ID)
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <div class="max-w-2xl">
      <h1 class="text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
        {{ t('votes.title') }}
      </h1>

      <p class="mt-2 text-sm leading-relaxed text-fino-text-muted">
        {{ company ? t('votes.description', { company: company.shortName }) : t('votes.descriptionShort') }}
      </p>
    </div>

    <div
      v-if="isLoading && !items.length"
      class="grid grid-cols-1 gap-4 md:grid-cols-2"
      aria-busy="true"
    >
      <VoteCardSkeleton
        v-for="index in VOTE_SKELETON_COUNT"
        :key="index"
      />
    </div>

    <AppErrorState
      v-else-if="error"
      :message="t('votes.loadError')"
      @retry="loadVotes"
    />

    <div
      v-else-if="!items.length"
      class="flex flex-col items-center rounded-3xl border border-dashed border-fino-border bg-fino-surface
             px-6 py-14 text-center"
    >
      <span class="flex size-14 items-center justify-center rounded-2xl bg-fino-accent text-primary">
        <i
          class="pi pi-check-square text-2xl"
          aria-hidden="true"
        />
      </span>

      <p class="mt-4 text-base font-bold text-fino-text">
        {{ t('votes.empty.title') }}
      </p>

      <p class="mt-1 max-w-sm text-sm text-fino-text-muted">
        {{ t('votes.empty.text') }}
      </p>

      <!-- Участник видит только голосование: объясняем роль и даём путь, а не тупик -->
      <p class="mt-3 max-w-md text-sm text-fino-text-muted">
        {{ t('votes.empty.role') }}
      </p>

      <button
        type="button"
        class="mt-4 inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border border-fino-border
               bg-fino-surface px-4 text-sm font-semibold text-fino-text transition-colors
               hover:bg-fino-surface-hover focus-visible:outline-2 focus-visible:outline-primary
               motion-reduce:transition-none"
        @click="openVoteScenario"
      >
        <i
          class="pi pi-compass text-primary"
          aria-hidden="true"
        />
        {{ t('votes.empty.scenario') }}
      </button>
    </div>

    <ul
      v-else
      class="grid grid-cols-1 gap-4 md:grid-cols-2"
    >
      <li
        v-for="item in items"
        :key="item.task.id"
      >
        <VoteCard
          :inn="inn"
          :item="item"
          :person-inn="me?.personInn ?? null"
          :today="demoPersona?.today ?? null"
        />
      </li>
    </ul>
  </div>
</template>
