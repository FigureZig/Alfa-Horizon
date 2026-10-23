<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

const props = defineProps<{
  persona: SandboxPersonaInterface
  isBusy: boolean
}>()

const emit = defineEmits<{
  login: [persona: SandboxPersonaInterface]
}>()

const { t } = useI18n({ useScope: 'global' })

const isBank = computed(() => props.persona.kind === SandboxPersonaKindEnum.Bank)

const avatarClass = computed(() =>
  isBank.value ? 'bg-primary text-primary-contrast' : 'bg-fino-accent text-primary',
)

function handleLogin() {
  emit('login', props.persona)
}
</script>

<template>
  <article
    class="group relative flex h-full min-w-0 flex-col gap-4 rounded-3xl border border-fino-border
           bg-fino-surface p-5 shadow-sm transition-all duration-300
           hover:-translate-y-1 hover:border-primary/40 hover:shadow-md
           has-focus-visible:outline-2 has-focus-visible:outline-primary
           motion-reduce:transition-none motion-reduce:hover:translate-y-0"
  >
    <div class="flex items-start justify-between gap-3">
      <div
        class="flex size-12 shrink-0 items-center justify-center rounded-2xl text-base font-bold"
        :class="avatarClass"
        aria-hidden="true"
      >
        {{ persona.initials }}
      </div>

      <span
        class="shrink-0 rounded-full bg-fino-surface-secondary px-2.5 py-1 text-xs font-semibold
               text-fino-text-muted"
      >
        {{ persona.badge }}
      </span>
    </div>

    <div class="min-w-0">
      <p class="break-words text-base font-bold tracking-tight text-fino-text">
        {{ persona.fullName }}
      </p>

      <p class="mt-0.5 break-words text-sm text-fino-text-muted">
        {{ persona.roleTitle }}
      </p>
    </div>

    <p class="line-clamp-3 text-sm leading-relaxed text-fino-text-muted">
      {{ persona.about }}
    </p>

    <!-- Вся карточка кликабельна: кнопка растянута на неё -->
    <button
      type="button"
      class="mt-auto inline-flex min-h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-xl
             border border-fino-border bg-fino-surface-secondary px-4 text-sm font-semibold text-fino-text
             transition-colors duration-200 group-hover:border-primary group-hover:bg-primary
             group-hover:text-primary-contrast after:absolute after:inset-0 after:rounded-3xl
             after:content-[''] focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60
             motion-reduce:transition-none"
      :disabled="isBusy"
      :aria-label="t('login.enterAs', { name: persona.fullName })"
      @click="handleLogin"
    >
      {{ t('login.enter') }}
      <i
        class="pi pi-arrow-right text-xs"
        aria-hidden="true"
      />
    </button>
  </article>
</template>
