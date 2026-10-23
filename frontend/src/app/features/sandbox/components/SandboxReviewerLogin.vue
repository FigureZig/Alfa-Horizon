<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { useLoginById } from '@/app/composables/useLoginById'

const EXAMPLES = ['s7', 's2', 'bank', 'risk']

const emit = defineEmits<{
  navigated: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { login, isSubmitting, errorMessage, submit } = useLoginById()

function selectExample(example: string) {
  login.value = example
}

async function handleSubmit() {
  if (await submit()) emit('navigated')
}
</script>

<template>
  <form
    class="flex flex-col gap-4"
    novalidate
    @submit.prevent="handleSubmit"
  >
    <p class="text-sm leading-relaxed text-fino-text-muted">
      {{ t('reviewer.login.description') }}
    </p>

    <div class="flex flex-col gap-2">
      <label
        for="reviewer-login"
        class="text-sm font-semibold text-fino-text"
      >
        {{ t('reviewer.login.label') }}
      </label>

      <InputText
        id="reviewer-login"
        v-model="login"
        placeholder="s7"
        autocomplete="off"
        :invalid="Boolean(errorMessage)"
        :disabled="isSubmitting"
        fluid
      />
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <span class="text-xs text-fino-text-muted">{{ t('reviewer.login.examples') }}</span>

      <button
        v-for="example in EXAMPLES"
        :key="example"
        type="button"
        class="cursor-pointer rounded-lg bg-fino-surface-secondary px-2.5 py-1 font-mono text-xs font-semibold
               text-fino-text transition-colors hover:bg-fino-surface-hover motion-reduce:transition-none"
        @click="selectExample(example)"
      >
        {{ example }}
      </button>
    </div>

    <Message
      v-if="errorMessage"
      severity="error"
      size="small"
      role="alert"
    >
      {{ errorMessage }}
    </Message>

    <button
      type="submit"
      class="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm
             font-semibold text-primary-contrast transition-opacity hover:opacity-90 disabled:cursor-not-allowed
             disabled:opacity-60 motion-reduce:transition-none"
      :disabled="isSubmitting || !login.trim()"
    >
      <i
        v-if="isSubmitting"
        class="pi pi-spin pi-spinner text-xs"
        aria-hidden="true"
      />
      {{ t('reviewer.login.submit') }}
    </button>
  </form>
</template>
