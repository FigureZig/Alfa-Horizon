<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import ApplicationApprovalPanel from './ApplicationApprovalPanel.vue'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { ApplicationAskEnum } from '@/app/types/application/application-ask-enum'
import type { ApplicationInfoAnswerInterface } from '@/app/types/application/application-form-interface'
import type {
  ApplicationApprovalInterface,
  ApplicationInfoRequestInterface,
} from '@/app/types/application/application-interface'
import type { ApplicationVoteEnum } from '@/app/types/application/application-vote-enum'
import type { Nullable } from '@/app/types/nullable'

const COMMENT_MAX_LENGTH = 2000
// Загрузка — имитация: файл мгновение «загружается» и встаёт в список, банку уходит его имя
const UPLOAD_DELAY = 700

interface AttachedDocumentInterface {
  id: number
  name: string
  isUploading: boolean
}

const props = defineProps<{
  infoRequest: Nullable<ApplicationInfoRequestInterface>
  approval: Nullable<ApplicationApprovalInterface>
  canAnswer: boolean
  canVote: boolean
  pendingAction: Nullable<ApplicationActionEnum>
}>()

const emit = defineEmits<{
  answer: [answer: ApplicationInfoAnswerInterface]
  vote: [choice: ApplicationVoteEnum]
}>()

const { t, locale } = useI18n({ useScope: 'global' })

const form = reactive({
  corporateApproval: false,
  collateralValue: null as Nullable<number>,
  comment: '',
})

const isSubmitted = ref(false)
// Готовое решение собрания загружают отдельным явным действием, а не рядом с голосованием
const isAnswerOpen = ref(false)
const attachedDocuments = ref<AttachedDocumentInterface[]>([])
const fileInput = useTemplateRef<HTMLInputElement>('fileInput')

let lastDocumentId = 0
const uploadTimers: number[] = []

const asks = computed(() => props.infoRequest?.asks ?? [])
const isCorpApprovalAsked = computed(() => asks.value.includes(ApplicationAskEnum.CorpApproval))
const isCollateralAsked = computed(() => asks.value.includes(ApplicationAskEnum.CollateralValue))
// Банк просит согласие участников, и они голосуют в продукте
const isVoting = computed(() => Boolean(props.approval) && isCorpApprovalAsked.value)
const isBusy = computed(() => props.pendingAction !== null)
const isAnswering = computed(() => props.pendingAction === ApplicationActionEnum.AnswerInfo)

const askTexts = computed(() => asks.value.map((ask) => t(`application.infoRequest.ask.${ask}`)))

const isUploading = computed(() => attachedDocuments.value.some((item) => item.isUploading))

const documents = computed(() =>
  attachedDocuments.value.filter((item) => !item.isUploading).map((item) => item.name),
)

// Нужен хоть какой-то ответ, а запрошенная стоимость залога — обязательна
const errorText = computed(() => {
  if (!isSubmitted.value) return null

  if (isCollateralAsked.value && form.collateralValue === null) {
    return t('application.infoRequest.collateralRequired')
  }

  const hasAnswer = form.corporateApproval || form.collateralValue !== null
    || documents.value.length > 0 || form.comment.trim()

  return hasAnswer ? null : t('application.infoRequest.emptyAnswer')
})

function handleSubmit() {
  isSubmitted.value = true

  if (errorText.value) return

  emit('answer', {
    corporateApproval: form.corporateApproval,
    collateralValue: form.collateralValue,
    documents: documents.value,
    comment: form.comment,
  })
}

function openAnswer() {
  isAnswerOpen.value = true
}

function openFilePicker() {
  fileInput.value?.click()
}

function finishUpload(id: number) {
  const attached = attachedDocuments.value.find((item) => item.id === id)

  if (attached) attached.isUploading = false
}

function handleFilesSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const names = Array.from(input.files ?? [], (file) => file.name)

  // Тот же файл можно выбрать снова после удаления
  input.value = ''

  for (const name of names) {
    if (attachedDocuments.value.some((item) => item.name === name)) continue

    const id = ++lastDocumentId

    attachedDocuments.value.push({ id, name, isUploading: true })
    uploadTimers.push(window.setTimeout(finishUpload, UPLOAD_DELAY, id))
  }
}

function removeDocument(id: number) {
  attachedDocuments.value = attachedDocuments.value.filter((item) => item.id !== id)
}

onBeforeUnmount(() => {
  uploadTimers.forEach((timer) => window.clearTimeout(timer))
})

function handleVote(choice: ApplicationVoteEnum) {
  emit('vote', choice)
}
</script>

<template>
  <section class="flex flex-col gap-5">
    <!-- При голосовании заголовок уже в блоке статуса сверху: здесь только пояснение -->
    <p
      v-if="isVoting"
      class="text-sm text-fino-text-muted"
    >
      {{ t('application.infoRequest.votingNote') }}
    </p>

    <div v-else>
      <h2 class="text-lg font-bold tracking-tight text-fino-text">
        {{ t('application.infoRequest.title') }}
      </h2>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ t('application.infoRequest.description') }}
      </p>
    </div>

    <ul
      v-if="askTexts.length && !isVoting"
      class="flex flex-col gap-2"
    >
      <li
        v-for="text in askTexts"
        :key="text"
        class="flex items-start gap-2 rounded-xl bg-fino-accent px-3 py-2 text-sm text-fino-text"
      >
        <i
          class="pi pi-exclamation-circle mt-0.5 text-primary"
          aria-hidden="true"
        />
        <span class="min-w-0 break-words">{{ text }}</span>
      </li>
    </ul>

    <p
      v-if="infoRequest?.comment"
      class="break-words rounded-xl bg-fino-surface-secondary p-3 text-sm text-fino-text"
    >
      {{ infoRequest.comment }}
    </p>

    <!-- Электронное голосование участников за крупную сделку -->
    <ApplicationApprovalPanel
      v-if="approval"
      :approval="approval"
      :can-vote="canVote"
      :pending-action="pendingAction"
      @vote="handleVote"
    />

    <button
      v-if="canAnswer && isVoting && !isAnswerOpen"
      type="button"
      class="w-fit cursor-pointer text-sm font-semibold text-primary transition-opacity hover:opacity-80
             focus-visible:outline-2 focus-visible:outline-primary"
      @click="openAnswer"
    >
      {{ t('application.infoRequest.uploadDecision') }}
    </button>

    <form
      v-if="canAnswer && (!isVoting || isAnswerOpen)"
      class="flex flex-col gap-4"
      novalidate
      @submit.prevent="handleSubmit"
    >
      <label
        v-if="isCorpApprovalAsked"
        class="flex cursor-pointer items-start gap-3 text-sm text-fino-text"
      >
        <Checkbox
          v-model="form.corporateApproval"
          binary
          :disabled="isBusy"
          class="mt-0.5 shrink-0"
        />
        <span>{{ t('application.infoRequest.corporateApproval') }}</span>
      </label>

      <div
        v-if="isCollateralAsked"
        class="flex flex-col gap-2"
      >
        <label
          for="info-collateral"
          class="text-sm font-semibold text-fino-text"
        >
          {{ t('application.infoRequest.collateralValue') }}
        </label>

        <InputNumber
          v-model="form.collateralValue"
          input-id="info-collateral"
          :min="1"
          :max-fraction-digits="0"
          suffix=" ₽"
          :locale="locale"
          :disabled="isBusy"
          :invalid="isSubmitted && form.collateralValue === null"
          fluid
        />
      </div>

      <!-- Документы: «Прикрепить» — файл появляется в списке с именем -->
      <div class="flex flex-col gap-2">
        <span class="text-sm font-semibold text-fino-text">
          {{ t('application.infoRequest.documents') }}
        </span>

        <ul
          v-if="attachedDocuments.length"
          class="flex flex-col gap-2"
          aria-live="polite"
        >
          <li
            v-for="item in attachedDocuments"
            :key="item.id"
            class="flex items-center gap-3 rounded-xl border border-fino-border bg-fino-surface px-3 py-2 text-sm"
          >
            <i
              :class="item.isUploading ? 'pi pi-spinner pi-spin text-fino-text-muted' : 'pi pi-file text-primary'"
              aria-hidden="true"
            />

            <span
              class="min-w-0 flex-1 truncate text-fino-text"
              :title="item.name"
            >{{ item.name }}</span>

            <span class="shrink-0 text-xs text-fino-text-muted">
              {{ item.isUploading ? t('application.infoRequest.uploading') : t('application.infoRequest.uploaded') }}
            </span>

            <button
              type="button"
              class="flex size-7 shrink-0 cursor-pointer items-center justify-center rounded-lg text-fino-text-muted
                     transition-colors hover:bg-fino-surface-hover hover:text-primary disabled:cursor-not-allowed
                     disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-primary"
              :aria-label="t('application.infoRequest.removeDocument', { name: item.name })"
              :title="t('application.infoRequest.removeDocument', { name: item.name })"
              :disabled="isBusy"
              @click="removeDocument(item.id)"
            >
              <i
                class="pi pi-times text-xs"
                aria-hidden="true"
              />
            </button>
          </li>
        </ul>

        <input
          ref="fileInput"
          type="file"
          multiple
          class="hidden"
          @change="handleFilesSelected"
        >

        <button
          type="button"
          class="inline-flex min-h-11 w-fit cursor-pointer items-center gap-2 rounded-xl border-dashed px-4 py-2.5 text-sm
                 font-semibold text-fino-text transition-colors duration-200 hover:border-primary hover:text-primary
                 disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none focus-visible:outline-2
                 focus-visible:outline-primary border-2 border-fino-line/40"
          :disabled="isBusy"
          @click="openFilePicker"
        >
          <i
            class="pi pi-paperclip text-xs"
            aria-hidden="true"
          />
          {{ t('application.infoRequest.attach') }}
        </button>
      </div>

      <div class="flex flex-col gap-2">
        <label
          for="info-comment"
          class="text-sm font-semibold text-fino-text"
        >
          {{ t('application.infoRequest.comment') }}
        </label>

        <Textarea
          id="info-comment"
          v-model="form.comment"
          :maxlength="COMMENT_MAX_LENGTH"
          rows="2"
          auto-resize
          :disabled="isBusy"
          fluid
        />
      </div>

      <Message
        v-if="errorText"
        severity="error"
        size="small"
        variant="simple"
      >
        {{ errorText }}
      </Message>

      <button
        type="submit"
        class="inline-flex min-h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3
               text-sm font-semibold text-primary-contrast sm:w-fit disabled:cursor-not-allowed disabled:opacity-60
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary btn-key"
        :disabled="isBusy || isUploading"
        :aria-busy="isAnswering"
      >
        <i
          v-if="isAnswering"
          class="pi pi-spinner pi-spin text-xs"
          aria-hidden="true"
        />
        {{ t('application.infoRequest.send') }}
      </button>
    </form>
  </section>
</template>
