<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

const props = defineProps<{
  persona: SandboxPersonaInterface
}>()

const emit = defineEmits<{
  login: [persona: SandboxPersonaInterface]
  loginAsOfficer: []
}>()

const { t } = useI18n({ useScope: 'global' })

const isBankPersona = computed(() => props.persona.kind === SandboxPersonaKindEnum.Bank)

const fields = computed(() => [
  { key: 'permissions', label: t('sandbox.details.permissions'), value: props.persona.permissions },
  { key: 'profile', label: t('sandbox.details.profile'), value: props.persona.profile },
  { key: 'registries', label: t('sandbox.details.registries'), value: props.persona.registries },
  { key: 'preview', label: t('sandbox.details.preview'), value: props.persona.preview },
])

function handleLogin() {
  emit('login', props.persona)
}

function handleLoginAsOfficer() {
  emit('loginAsOfficer')
}
</script>

<template>
  <section
    class="flex min-w-0 flex-col gap-6 rounded-3xl border border-fino-border
           bg-fino-surface p-5 shadow-sm sm:p-6"
    :aria-label="t('sandbox.details.title')"
  >
    <!-- Заголовок -->
    <div class="flex items-center gap-4">
      <div
        class="flex size-14 shrink-0 items-center justify-center rounded-full
               bg-fino-accent text-lg font-bold text-primary"
        aria-hidden="true"
      >
        {{ persona.initials }}
      </div>

      <div class="min-w-0">
        <h2 class="break-words text-xl font-bold tracking-tight text-fino-text">
          {{ persona.fullName }}
        </h2>

        <p class="mt-1 break-words text-sm text-fino-text-muted">
          {{ persona.organization }}
        </p>
      </div>
    </div>

    <dl class="flex flex-col divide-y divide-fino-border">
      <!-- Сценарий -->
      <div class="pb-4">
        <dt class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
          {{ t('sandbox.details.scenario') }}
        </dt>

        <dd class="mt-2 flex items-start gap-2">
          <span
            class="shrink-0 rounded-lg bg-fino-accent px-2 py-0.5
                   text-xs font-semibold text-primary"
          >
            {{ persona.code }}
          </span>

          <span class="min-w-0 break-words text-sm font-medium text-fino-text">
            {{ persona.scenario }}
          </span>
        </dd>
      </div>

      <!-- Права, профиль, реестры, что увидите -->
      <div
        v-for="field in fields"
        :key="field.key"
        class="py-4 last:pb-0"
      >
        <dt class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
          {{ field.label }}
        </dt>

        <dd class="mt-1.5 break-words text-sm leading-relaxed text-fino-text">
          {{ field.value }}
        </dd>
      </div>
    </dl>

    <div class="flex flex-col gap-3">
      <button
        type="button"
        class="inline-flex min-h-12 w-full cursor-pointer items-center justify-center
               gap-2 rounded-xl bg-primary px-5 py-3 text-center text-sm font-semibold
               text-primary-contrast transition-all duration-200
               hover:opacity-90 active:scale-95
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary
               motion-reduce:transition-none"
        @click="handleLogin"
      >
        {{ persona.loginLabel }}
        <i
          class="pi pi-arrow-right text-xs"
          aria-hidden="true"
        />
      </button>

      <button
        v-if="!isBankPersona"
        type="button"
        class="inline-flex min-h-12 w-full cursor-pointer items-center justify-center
               rounded-xl border border-fino-border bg-fino-surface px-5 py-3
               text-center text-sm font-semibold text-fino-text
               transition-colors duration-200 hover:bg-fino-surface-hover
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary
               motion-reduce:transition-none"
        @click="handleLoginAsOfficer"
      >
        {{ t('sandbox.loginAsOfficer') }}
      </button>
    </div>
  </section>
</template>
