<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import SandboxPersonaBuilderPromo from '@/app/features/sandbox/components/SandboxPersonaBuilderPromo.vue'
import SandboxDemoBadge from '@/app/features/sandbox/components/SandboxDemoBadge.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxMapper } from '@/app/mappers/sandbox.mapper'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { SandboxPersonaFormInterface } from '@/app/types/sandbox/sandbox-persona-form-interface'
import type { Nullable } from '@/app/types/nullable'

type TextFieldKey = Exclude<keyof SandboxPersonaFormInterface, 'kind'>

interface FormFieldInterface {
  key: TextFieldKey
  isMultiline: boolean
  maxLength: number
  colSpanClass: string
  inputMode?: 'numeric'
}

// Формат ИНН как в API: 10 цифр — юрлицо, 12 — ИП
const INN_PATTERN = /^(\d{10}|\d{12})$/

const FORM_FIELDS: FormFieldInterface[] = [
  { key: 'fullName', isMultiline: false, maxLength: 80, colSpanClass: 'lg:col-span-4' },
  { key: 'organization', isMultiline: false, maxLength: 120, colSpanClass: 'lg:col-span-5' },
  { key: 'code', isMultiline: false, maxLength: 8, colSpanClass: 'lg:col-span-3' },
  { key: 'inn', isMultiline: false, maxLength: 12, colSpanClass: 'lg:col-span-3', inputMode: 'numeric' },
  { key: 'loginLabel', isMultiline: false, maxLength: 60, colSpanClass: 'lg:col-span-3' },
  { key: 'scenario', isMultiline: false, maxLength: 120, colSpanClass: 'lg:col-span-6' },
  { key: 'permissions', isMultiline: true, maxLength: 300, colSpanClass: 'lg:col-span-6' },
  { key: 'profile', isMultiline: true, maxLength: 300, colSpanClass: 'lg:col-span-6' },
  { key: 'registries', isMultiline: true, maxLength: 300, colSpanClass: 'lg:col-span-6' },
  { key: 'preview', isMultiline: true, maxLength: 300, colSpanClass: 'lg:col-span-6' },
]

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const toast = useToast()
const $fetch = useApiFetch()

const form = reactive<SandboxPersonaFormInterface>({
  kind: SandboxPersonaKindEnum.Client,
  fullName: '',
  inn: '',
  organization: '',
  code: '',
  scenario: '',
  permissions: '',
  profile: '',
  registries: '',
  preview: '',
  loginLabel: '',
})

const isSubmitting = ref(false)
const isSubmitted = ref(false)

const kindOptions = computed(() => [
  { value: SandboxPersonaKindEnum.Client, label: t('sandbox.builder.kind.client') },
  { value: SandboxPersonaKindEnum.Bank, label: t('sandbox.builder.kind.bank') },
])

function getFieldError(key: TextFieldKey): Nullable<string> {
  const value = form[key].trim()

  if (!value) return t('sandbox.builder.required')
  if (key === 'inn' && !INN_PATTERN.test(value)) return t('sandbox.builder.innInvalid')

  return null
}

const fields = computed(() =>
  FORM_FIELDS.map((field) => {
    const error = isSubmitted.value ? getFieldError(field.key) : null

    return {
      ...field,
      label: t(`sandbox.builder.fields.${field.key}.label`),
      placeholder: t(`sandbox.builder.fields.${field.key}.placeholder`),
      error,
      isInvalid: Boolean(error),
    }
  }),
)

const isFormValid = computed(() => fields.value.every((field) => !field.isInvalid))

async function submitPersona() {
  if (isSubmitting.value) return

  isSubmitted.value = true

  if (!isFormValid.value) return

  isSubmitting.value = true

  try {
    await sandboxService.createPersona($fetch, SandboxMapper.toPayload(form))

    toast.add({
      severity: 'success',
      summary: t('toast.success'),
      detail: t('sandbox.builder.createSuccess'),
      life: 4000,
    })

    await router.push({ name: 'sandbox' })
  } catch (err: unknown) {
    console.error('Sandbox persona creation failed:', err)

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: t('toast.sandboxCreateError'),
      life: 4000,
    })
  } finally {
    isSubmitting.value = false
  }
}

function cancelBuilding() {
  router.push({ name: 'sandbox' })
}
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader>
      <template #profile>
        <SandboxDemoBadge />
      </template>
    </AppHeader>

    <main class="mx-auto flex max-w-[1600px] flex-col gap-6 px-4 py-6 sm:px-6">
      <!-- Заголовок -->
      <div>
        <RouterLink
          :to="{ name: 'sandbox' }"
          class="inline-flex items-center gap-2 text-sm font-semibold text-primary
                 transition-opacity hover:opacity-80"
        >
          <i
            class="pi pi-arrow-left text-xs"
            aria-hidden="true"
          />
          {{ t('sandbox.builder.back') }}
        </RouterLink>

        <h1 class="mt-3 text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
          {{ t('sandbox.builder.title') }}
        </h1>

        <p class="mt-2 max-w-2xl text-sm leading-relaxed text-fino-text-muted">
          {{ t('sandbox.builder.description') }}
        </p>
      </div>

      <div class="grid grid-cols-1 items-stretch gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <form
          class="flex min-w-0 flex-col gap-5 rounded-3xl border border-fino-border
               bg-fino-surface p-5 shadow-sm sm:p-6"
          novalidate
          :aria-busy="isSubmitting"
          @submit.prevent="submitPersona"
        >
          <!-- Тип персоны -->
          <div class="flex flex-col gap-2">
            <span class="text-sm font-semibold text-fino-text">
              {{ t('sandbox.builder.kind.label') }}
            </span>

            <SelectButton
              v-model="form.kind"
              :options="kindOptions"
              option-label="label"
              option-value="value"
              :allow-empty="false"
              :aria-label="t('sandbox.builder.kind.label')"
            />
          </div>

          <!-- Поля -->
          <div class="grid grid-cols-1 gap-4 lg:grid-cols-12">
            <div
              v-for="field in fields"
              :key="field.key"
              class="flex min-w-0 flex-col gap-2"
              :class="field.colSpanClass"
            >
              <label
                :for="`persona-${field.key}`"
                class="text-sm font-semibold text-fino-text"
              >
                {{ field.label }}
              </label>

              <Textarea
                v-if="field.isMultiline"
                :id="`persona-${field.key}`"
                v-model="form[field.key]"
                :placeholder="field.placeholder"
                :maxlength="field.maxLength"
                :invalid="field.isInvalid"
                :disabled="isSubmitting"
                rows="2"
                auto-resize
                fluid
              />

              <InputText
                v-else
                :id="`persona-${field.key}`"
                v-model="form[field.key]"
                :placeholder="field.placeholder"
                :maxlength="field.maxLength"
                :inputmode="field.inputMode"
                :invalid="field.isInvalid"
                :disabled="isSubmitting"
                fluid
              />

              <Message
                v-if="field.isInvalid"
                severity="error"
                size="small"
                variant="simple"
              >
                {{ field.error }}
              </Message>
            </div>
          </div>

          <!-- Действия -->
          <div class="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button
              type="button"
              severity="secondary"
              :label="t('sandbox.builder.cancel')"
              :disabled="isSubmitting"
              @click="cancelBuilding"
            />

            <Button
              type="submit"
              :label="t('sandbox.builder.submit')"
              icon="pi pi-check"
              :loading="isSubmitting"
            />
          </div>
        </form>

        <SandboxPersonaBuilderPromo class="hidden xl:flex" />
      </div>
    </main>
  </div>
</template>
