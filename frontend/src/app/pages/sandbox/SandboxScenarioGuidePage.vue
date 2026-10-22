<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Skeleton from 'primevue/skeleton'
import AppErrorState from '@/app/components/AppErrorState.vue'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import ApplicationStatusBadge from '@/app/features/application/components/ApplicationStatusBadge.vue'
import SandboxDemoBadge from '@/app/features/sandbox/components/SandboxDemoBadge.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useSession } from '@/app/composables/useSession'
import { applicationsService } from '@/app/services/application/applications.service'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { ApplicationMapper } from '@/app/mappers/application.mapper'
import { SandboxMapper } from '@/app/mappers/sandbox.mapper'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import { ApprovalStatusEnum } from '@/app/types/application/approval-status-enum'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { ApplicationInterface } from '@/app/types/application/application-interface'
import type { AppLocale } from '@/app/i18n'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

const props = defineProps<{ inn: string }>()

const { t, locale } = useI18n({ useScope: 'global' })
const route = useRoute()
const router = useRouter()
const toast = useToast()
const $fetch = useApiFetch()
const { loginAsPersona } = useSession()

const personas = ref<SandboxPersonaInterface[]>([])
const application = ref<Nullable<ApplicationInterface>>(null)
const isLoading = ref(false)
const hasError = ref(false)
const applicationUnavailable = ref(false)
const switchingPersonaId = ref<Nullable<string>>(null)

let requestId = 0

const owner = computed(() => personas.value[0] ?? null)
const approval = computed(() => application.value?.approval ?? null)
const isVotingOpen = computed(() => approval.value?.status === ApprovalStatusEnum.Open)
const isIssued = computed(() => application.value?.status === ApplicationDetailStatusEnum.Issued)
const isSwitching = computed(() => switchingPersonaId.value !== null)

const members = computed(() => {
  const participants = approval.value?.participants
  const cards = participants
    ? personas.value.filter((persona) => participants.some((member) => member.inn === persona.personInn))
    : personas.value

  return cards.map((persona) => {
    const participant = participants?.find((member) => member.inn === persona.personInn)
    const vote = approval.value?.votes.find((item) => item.inn === persona.personInn)?.vote ?? null

    return { persona, share: participant?.share ?? null, vote }
  })
})

const progressWidth = computed(() => ({ width: `${Math.min(approval.value?.forPercent ?? 0, 100)}%` }))

async function loadGuide() {
  const currentRequest = ++requestId
  isLoading.value = true
  hasError.value = false
  applicationUnavailable.value = false
  application.value = null

  try {
    const { data } = await sandboxService.fetchPersonas($fetch, locale.value as AppLocale)
    if (currentRequest !== requestId) return

    personas.value = data.data
      .filter((persona) => persona.kind === SandboxPersonaKindEnum.Client && persona.inn === props.inn)
      .map((persona) => SandboxMapper.toEntity(persona))

    const requestedId = typeof route.query.applicationId === 'string' ? route.query.applicationId : null

    try {
      if (requestedId) {
        const response = await applicationsService.fetchApplication($fetch, requestedId)
        if (currentRequest === requestId && response.data.data.company_inn === props.inn) {
          application.value = ApplicationMapper.toEntity(response.data.data)
        }
      } else {
        const response = await applicationsService.fetchApplications($fetch, props.inn)
        if (currentRequest === requestId && response.data.data[0]) {
          application.value = ApplicationMapper.toEntity(response.data.data[0])
        }
      }
    } catch (err: unknown) {
      if (currentRequest !== requestId) return
      console.error('Scenario guide application loading failed:', err)
      applicationUnavailable.value = true
    }
  } catch (err: unknown) {
    if (currentRequest !== requestId) return
    console.error('Scenario guide persona loading failed:', err)
    hasError.value = true
  } finally {
    if (currentRequest === requestId) isLoading.value = false
  }
}

async function enterAs(persona: SandboxPersonaInterface) {
  if (isSwitching.value) return
  switchingPersonaId.value = persona.id

  try {
    await loginAsPersona(persona.id)

    let applicationId = application.value?.id
    if (!applicationId) {
      const response = await applicationsService.fetchApplications($fetch, props.inn)
      applicationId = response.data.data[0]?.id
    }

    if (applicationId) {
      await router.push({ name: 'application', params: { inn: props.inn, applicationId }, query: { guide: props.inn } })
    } else {
      await router.push({ name: persona.id === owner.value?.id ? 'application-new' : 'applications',
        params: { inn: props.inn }, query: { guide: props.inn } })
    }
  } catch (err: unknown) {
    console.error('Scenario guide login failed:', err)
    toast.add({ severity: 'error', summary: t('toast.error'), detail: t('sandbox.guide.loginError'), life: 4000 })
  } finally {
    switchingPersonaId.value = null
  }
}

function enterAsOwner() {
  if (owner.value) void enterAs(owner.value)
}

function enterAsMember(persona: SandboxPersonaInterface) {
  void enterAs(persona)
}

function refreshGuide() {
  void loadGuide()
}

watch([() => props.inn, () => route.query.applicationId, locale], loadGuide, { immediate: true })
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader>
      <template #profile>
        <SandboxDemoBadge />
      </template>
    </AppHeader>

    <main class="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8">
      <div>
        <RouterLink
          :to="{ name: 'sandbox' }"
          class="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:opacity-80"
        >
          <i
            class="pi pi-arrow-left text-xs"
            aria-hidden="true"
          />
          {{ t('sandbox.guide.back') }}
        </RouterLink>

        <div class="mt-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p class="text-xs font-bold uppercase tracking-widest text-primary">
              {{ t('sandbox.guide.eyebrow') }}
            </p>
            <h1 class="mt-2 text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
              {{ t('sandbox.guide.title') }}
            </h1>
            <p class="mt-2 max-w-2xl text-sm leading-relaxed text-fino-text-muted">
              {{ t('sandbox.guide.description') }}
            </p>
          </div>

          <button
            type="button"
            class="inline-flex min-h-11 items-center gap-2 rounded-xl border border-fino-border
                   bg-fino-surface px-4 text-sm font-semibold text-fino-text hover:border-primary"
            :disabled="isLoading"
            @click="refreshGuide"
          >
            <i
              class="pi pi-refresh text-xs"
              aria-hidden="true"
            />
            {{ t('sandbox.guide.refresh') }}
          </button>
        </div>
      </div>

      <div
        v-if="isLoading"
        class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]"
        aria-busy="true"
      >
        <div class="flex flex-col gap-4">
          <Skeleton
            v-for="step in 3"
            :key="step"
            height="10rem"
            border-radius="1.5rem"
          />
        </div>
        <Skeleton
          height="15rem"
          border-radius="1.5rem"
        />
      </div>

      <AppErrorState
        v-else-if="hasError"
        :message="t('sandbox.guide.loadError')"
        is-inline
        @retry="refreshGuide"
      />

      <div
        v-else-if="!owner"
        class="rounded-3xl border border-fino-border bg-fino-surface p-6"
      >
        <p class="text-sm text-fino-text-muted">
          {{ t('sandbox.guide.noPersonas') }}
        </p>
        <RouterLink
          :to="{ name: 'sandbox' }"
          class="mt-3 inline-flex text-sm font-semibold text-primary"
        >
          {{ t('sandbox.guide.back') }}
        </RouterLink>
      </div>

      <div
        v-else
        class="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]"
      >
        <div class="flex min-w-0 flex-col gap-4">
          <section class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6">
            <div class="flex items-start gap-4">
              <span class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-fino-accent font-bold text-primary">1</span>
              <div class="min-w-0 flex-1">
                <h2 class="text-lg font-bold text-fino-text">
                  {{ t('sandbox.guide.createTitle') }}
                </h2>
                <p class="mt-1 text-sm leading-relaxed text-fino-text-muted">
                  {{ t('sandbox.guide.createHint') }}
                </p>
                <p class="mt-4 text-sm font-semibold text-fino-text">
                  {{ owner.fullName }}
                </p>
                <button
                  type="button"
                  class="mt-3 inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-4
                         text-sm font-semibold text-primary-contrast hover:opacity-90
                         disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="isSwitching"
                  @click="enterAsOwner"
                >
                  <i
                    class="pi pi-sign-in text-xs"
                    aria-hidden="true"
                  />
                  {{ application ? t('sandbox.guide.openAsOwner') : t('sandbox.guide.createAsOwner') }}
                </button>
              </div>
              <i
                v-if="application"
                class="pi pi-check-circle text-xl text-green-600 dark:text-green-400"
                aria-hidden="true"
              />
            </div>
          </section>

          <section class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6">
            <div class="flex items-start gap-4">
              <span class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-fino-accent font-bold text-primary">2</span>
              <div class="min-w-0 flex-1">
                <h2 class="text-lg font-bold text-fino-text">
                  {{ t('sandbox.guide.voteTitle') }}
                </h2>
                <p class="mt-1 text-sm leading-relaxed text-fino-text-muted">
                  {{ t('sandbox.guide.voteHint') }}
                </p>

                <p
                  v-if="!application"
                  class="mt-4 text-sm text-fino-text-muted"
                >
                  {{ t('sandbox.guide.noApplication') }}
                </p>
                <p
                  v-else-if="!approval"
                  class="mt-4 text-sm text-fino-text-muted"
                >
                  {{ t('sandbox.guide.waitingForVote') }}
                </p>
                <p
                  v-else-if="approval.status === ApprovalStatusEnum.Approved"
                  class="mt-4 text-sm font-semibold text-green-700 dark:text-green-400"
                >
                  {{ t('sandbox.guide.approved') }}
                </p>
                <p
                  v-else-if="approval.status === ApprovalStatusEnum.Rejected"
                  class="mt-4 text-sm font-semibold text-red-700 dark:text-red-400"
                >
                  {{ t('sandbox.guide.rejected') }}
                </p>
                <p
                  v-else
                  class="mt-4 text-sm font-semibold text-primary"
                >
                  {{ t('sandbox.guide.voteOpen') }}
                </p>

                <ul class="mt-4 divide-y divide-fino-border">
                  <li
                    v-for="member in members"
                    :key="member.persona.id"
                    class="flex flex-wrap items-center justify-between gap-3 py-3"
                  >
                    <div class="min-w-0">
                      <p class="break-words text-sm font-semibold text-fino-text">
                        {{ member.persona.fullName }}
                      </p>
                      <p class="text-xs text-fino-text-muted">
                        {{ member.share === null ? member.persona.scenario : t('application.approval.share', { share: member.share }) }}
                        <span v-if="member.vote"> · {{ t(`application.approval.vote.${member.vote}`) }}</span>
                      </p>
                    </div>
                    <button
                      v-if="isVotingOpen"
                      type="button"
                      class="inline-flex min-h-10 items-center gap-2 rounded-xl border border-fino-border px-3
                             text-xs font-semibold text-primary hover:border-primary
                             disabled:cursor-not-allowed disabled:opacity-60"
                      :disabled="isSwitching"
                      @click="enterAsMember(member.persona)"
                    >
                      {{ t('sandbox.guide.voteAs') }}
                      <i
                        class="pi pi-arrow-right text-xs"
                        aria-hidden="true"
                      />
                    </button>
                  </li>
                </ul>
              </div>
            </div>
          </section>

          <section class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6">
            <div class="flex items-start gap-4">
              <span class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-fino-accent font-bold text-primary">3</span>
              <div class="min-w-0 flex-1">
                <h2 class="text-lg font-bold text-fino-text">
                  {{ t('sandbox.guide.finishTitle') }}
                </h2>
                <p class="mt-1 text-sm leading-relaxed text-fino-text-muted">
                  {{ t('sandbox.guide.finishHint') }}
                </p>
                <p
                  v-if="isIssued"
                  class="mt-4 text-sm font-semibold text-green-700 dark:text-green-400"
                >
                  {{ t('sandbox.guide.issued') }}
                </p>
                <button
                  v-else-if="application"
                  type="button"
                  class="mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl border border-fino-border px-4
                         text-sm font-semibold text-primary hover:border-primary
                         disabled:cursor-not-allowed disabled:opacity-60"
                  :disabled="isSwitching"
                  @click="enterAsOwner"
                >
                  {{ t('sandbox.guide.openAsOwner') }}
                  <i
                    class="pi pi-arrow-right text-xs"
                    aria-hidden="true"
                  />
                </button>
              </div>
              <i
                v-if="isIssued"
                class="pi pi-check-circle text-xl text-green-600 dark:text-green-400"
                aria-hidden="true"
              />
            </div>
          </section>
        </div>

        <aside class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6 lg:sticky lg:top-28">
          <p class="text-xs font-bold uppercase tracking-wide text-fino-text-muted">
            {{ t('sandbox.guide.application') }}
          </p>
          <p class="mt-2 break-words text-sm font-semibold text-fino-text">
            {{ owner.organization }}
          </p>

          <p
            v-if="applicationUnavailable"
            class="mt-4 text-xs leading-relaxed text-fino-text-muted"
          >
            {{ t('sandbox.guide.applicationUnavailable') }}
          </p>

          <template v-if="application">
            <div class="mt-5 flex flex-wrap items-center gap-2">
              <span class="text-xs text-fino-text-muted">№ {{ application.id }}</span>
              <ApplicationStatusBadge :status="application.status" />
            </div>

            <div
              v-if="approval"
              class="mt-5 border-t border-fino-border pt-5"
            >
              <p class="text-sm font-semibold text-fino-text">
                {{ t('sandbox.guide.voteProgress') }}
              </p>
              <div class="mt-3 h-2 overflow-hidden rounded-full bg-fino-surface-secondary">
                <div
                  class="h-full rounded-full bg-green-500"
                  :style="progressWidth"
                />
              </div>
              <p class="mt-2 text-xs text-fino-text-muted">
                {{ t('sandbox.guide.votesFor', { percent: approval.forPercent, threshold: approval.thresholdPercent }) }}
              </p>
            </div>

            <RouterLink
              :to="{ name: 'application', params: { inn, applicationId: application.id }, query: { guide: inn } }"
              class="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl
                     bg-fino-accent px-4 text-sm font-semibold text-primary hover:opacity-80"
            >
              {{ t('sandbox.guide.openApplication') }}
              <i
                class="pi pi-arrow-right text-xs"
                aria-hidden="true"
              />
            </RouterLink>
          </template>
          <p
            v-else
            class="mt-4 text-sm leading-relaxed text-fino-text-muted"
          >
            {{ t('sandbox.guide.noApplicationAside') }}
          </p>
        </aside>
      </div>
    </main>
  </div>
</template>
