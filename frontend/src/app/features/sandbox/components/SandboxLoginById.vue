<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { useLoginById } from '@/app/composables/useLoginById'

const { t } = useI18n({ useScope: 'global' })
const { login, isSubmitting, errorMessage, submit } = useLoginById()
</script>

<template>
  <form
    class="flex max-w-xl flex-col gap-2"
    novalidate
    @submit.prevent="submit"
  >
    <label
      for="login-by-id"
      class="text-sm font-semibold text-fino-text"
    >
      {{ t('login.byId.label') }}
    </label>

    <div class="flex flex-col gap-2 sm:flex-row">
      <InputText
        id="login-by-id"
        v-model="login"
        :placeholder="t('login.byId.placeholder')"
        autocomplete="off"
        :invalid="Boolean(errorMessage)"
        :disabled="isSubmitting"
        fluid
      />

      <button
        type="submit"
        class="inline-flex min-h-12 shrink-0 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-6
               text-sm font-semibold text-primary-contrast transition-all duration-200 hover:opacity-90 active:scale-95
               disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :disabled="isSubmitting || !login.trim()"
      >
        <i
          v-if="isSubmitting"
          class="pi pi-spin pi-spinner text-xs"
          aria-hidden="true"
        />
        {{ t('login.enter') }}
      </button>
    </div>

    <Message
      v-if="errorMessage"
      severity="error"
      size="small"
      variant="simple"
      role="alert"
    >
      {{ errorMessage }}
    </Message>
  </form>
</template>
