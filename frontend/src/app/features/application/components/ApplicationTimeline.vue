<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { ApplicationEventInterface } from '@/app/types/application/application-event-interface'

interface EventViewInterface {
  icon: string
  key: string
}

// Тип события бэкенда → иконка и ключ текста; неизвестные типы показываем общей строкой
const EVENT_VIEWS: Record<string, EventViewInterface> = {
  'application.status_changed': { icon: 'pi pi-flag', key: 'statusChanged' },
  'step.changed': { icon: 'pi pi-database', key: 'stepChanged' },
  'decision.made': { icon: 'pi pi-verified', key: 'decisionMade' },
  'decision.awaiting_second_key': { icon: 'pi pi-key', key: 'awaitingSecondKey' },
  'decision.second_key_returned': { icon: 'pi pi-replay', key: 'secondKeyReturned' },
  'signature.added': { icon: 'pi pi-pen-to-square', key: 'signatureAdded' },
  'approval.voted': { icon: 'pi pi-users', key: 'approvalVoted' },
  'application.flagged': { icon: 'pi pi-info-circle', key: 'flagged' },
  'provisional.confirmed': { icon: 'pi pi-check', key: 'provisionalConfirmed' },
}

const DEFAULT_VIEW: EventViewInterface = { icon: 'pi pi-circle', key: 'other' }
const ACTOR_KINDS = ['client', 'bank', 'worker', 'engine', 'timer']

const props = defineProps<{
  events: ApplicationEventInterface[]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatDateTime } = useFormatters()

function getEventTitle(event: ApplicationEventInterface, key: string): string {
  const payload = event.payload

  if (key === 'statusChanged') {
    // Первая запись — создание черновика
    return payload.from === null
      ? t('application.timeline.created')
      : t('application.timeline.statusChanged', { status: t(`application.status.${String(payload.to)}`) })
  }

  if (key === 'stepChanged') {
    return t(`application.timeline.step.${String(payload.state)}`)
  }

  if (key === 'decisionMade') {
    return t('application.timeline.decisionMade', { outcome: t(`application.outcome.${String(payload.outcome)}`) })
  }

  if (key === 'approvalVoted') {
    return t('application.timeline.approvalVoted')
  }

  return t(`application.timeline.${key}`)
}

function getActorLabel(actor: string): string {
  const kind = actor.split(':')[0]

  return ACTOR_KINDS.includes(kind) ? t(`application.timeline.actor.${kind}`) : ''
}

// Новые события сверху
const items = computed(() =>
  [...props.events].reverse().map((event) => {
    const view = EVENT_VIEWS[event.type] ?? DEFAULT_VIEW

    return {
      id: event.id,
      icon: view.icon,
      title: getEventTitle(event, view.key),
      meta: [
        formatDateTime(event.at, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        getActorLabel(event.actor),
      ].filter(Boolean).join(' · '),
    }
  }),
)
</script>

<template>
  <section :aria-label="t('application.timeline.title')">
    <h2 class="text-sm font-semibold text-fino-text">
      {{ t('application.timeline.title') }}
    </h2>

    <TransitionGroup
      tag="ol"
      class="mt-4 flex flex-col"
      enter-active-class="transition duration-300 ease-out motion-reduce:transition-none"
      enter-from-class="-translate-y-2 opacity-0"
    >
      <li
        v-for="item in items"
        :key="item.id"
        class="relative flex gap-3 pb-4 last:pb-0"
      >
        <span
          class="absolute top-7 bottom-0 left-3.5 w-px bg-fino-border last:hidden"
          aria-hidden="true"
        />

        <span
          class="relative flex size-7 shrink-0 items-center justify-center rounded-full
                 bg-fino-surface-secondary text-fino-text-muted"
          aria-hidden="true"
        >
          <i
            :class="item.icon"
            class="text-xs"
          />
        </span>

        <div class="min-w-0 pt-0.5">
          <p class="break-words text-sm text-fino-text">
            {{ item.title }}
          </p>

          <p class="mt-0.5 text-xs text-fino-text-muted">
            {{ item.meta }}
          </p>
        </div>
      </li>
    </TransitionGroup>
  </section>
</template>
