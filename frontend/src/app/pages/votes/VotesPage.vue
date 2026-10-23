<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import VoteCard from '@/app/features/votes/components/VoteCard.vue'
import VoteCardSkeleton from '@/app/features/votes/components/VoteCardSkeleton.vue'
import { useCompanyAccess } from '@/app/composables/useCompanyAccess'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useVoteTasks } from '@/app/composables/useVoteTasks'

const VOTE_SKELETON_COUNT = 2

const props = defineProps<{
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { demoPersona } = useDemoPersona()
const { me, company } = useCompanyAccess(() => props.inn)
const { items, isLoading, error, loadVotes } = useVoteTasks(() => props.inn)
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
