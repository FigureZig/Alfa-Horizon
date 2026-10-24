<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Drawer from 'primevue/drawer'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import SandboxReviewerGuide from './SandboxReviewerGuide.vue'
import SandboxReviewerScenarios from './SandboxReviewerScenarios.vue'
import SandboxWorldControls from './SandboxWorldControls.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { applicationsService } from '@/app/services/application/applications.service'
import { ApplicationMapper } from '@/app/mappers/application.mapper'
import type { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { Nullable } from '@/app/types/nullable'

const HINT_STORAGE_KEY = 'fino-reviewer-hint'
const BANK_ROUTE_PREFIX = 'bank-'

const { t } = useI18n({ useScope: 'global' })
const route = useRoute()
const $fetch = useApiFetch()

const isVisible = ref(false)
const activeTab = ref('scenarios')
const applicationStatus = ref<Nullable<ApplicationDetailStatusEnum>>(null)
const loadedApplicationInn = ref<Nullable<string>>(null)
// Срок текущего шага заявки на экране: к нему можно перемотать время мира
const deadlineAt = ref<Nullable<string>>(null)

function readHintDismissed(): boolean {
  try {
    return localStorage.getItem(HINT_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

const isHintDismissed = ref(readHintDismissed())

const applicationId = computed(() => (typeof route.params.applicationId === 'string' ? route.params.applicationId : null))
const inn = computed(() => (typeof route.params.inn === 'string' ? route.params.inn : undefined))

// События и отказы относятся к компании клиента; на рабочем месте банка ИНН компании подставлять не из чего
const eventInn = computed(() => (String(route.name ?? '').startsWith(BANK_ROUTE_PREFIX) ? undefined : inn.value))

// Компания открытой заявки — из самой заявки; участнику её не открыть (403), тогда — из адреса кабинета
const applicationInn = computed(() =>
  loadedApplicationInn.value ?? (applicationId.value ? eventInn.value ?? null : null),
)

// Подсказка проверяющему — один раз и только на экране входа, рядом с кнопкой
const isHintVisible = computed(() => route.name === 'login' && !isHintDismissed.value && !isVisible.value)

// После первого показа кнопка сжимается до иконки и не закрывает карточки
const isLabelVisible = computed(() => !isHintDismissed.value)

// В кабинете снизу мобильная навигация: кнопка стоит над ней
const positionClass = computed(() => {
  // В конструкторе снизу полоса предпросмотра
  if (route.name === 'login-company' || route.name === 'login-company-edit') return 'bottom-24 lg:bottom-6'

  return inn.value ? 'bottom-24 lg:bottom-6' : 'bottom-4 sm:bottom-6'
})

function openPanel() {
  isVisible.value = true
}

function closePanel() {
  isVisible.value = false
}

function handleVisibleChange(visible: boolean) {
  isVisible.value = visible
}

function dismissHint() {
  isHintDismissed.value = true

  try {
    localStorage.setItem(HINT_STORAGE_KEY, 'true')
  } catch {
    // Хранилище недоступно: подсказка покажется снова при следующем входе на экран
  }
}

// Статус заявки на экране — для галочек в сценариях; чужая заявка (403) просто не отмечается
async function loadApplicationStatus() {
  applicationStatus.value = null
  loadedApplicationInn.value = null
  deadlineAt.value = null

  if (!applicationId.value) return

  try {
    const { data } = await applicationsService.fetchApplication($fetch, applicationId.value)
    const application = ApplicationMapper.toEntity(data.data)

    applicationStatus.value = application.status
    loadedApplicationInn.value = application.companyInn
    deadlineAt.value = application.deadline?.status === application.status ? application.deadline.at : null
  } catch (err: unknown) {
    console.error('Reviewer application status loading failed:', err)
  }
}

watch([isVisible, applicationId], ([visible]) => {
  if (visible) loadApplicationStatus()
})
</script>

<template>
  <div
    class="fixed right-4 z-40 flex flex-col items-end gap-3 sm:right-6"
    :class="positionClass"
  >
    <!-- Одна тихая подсказка на экране входа -->
    <Transition
      enter-active-class="transition duration-300 ease-out motion-reduce:transition-none"
      enter-from-class="translate-y-2 opacity-0"
      leave-active-class="transition duration-150 ease-in motion-reduce:transition-none"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isHintVisible"
        class="w-72 max-w-[calc(100vw-2rem)] rounded-2xl border border-fino-border bg-fino-surface p-4 shadow-lg"
        role="status"
      >
        <p class="text-sm leading-relaxed text-fino-text">
          {{ t('reviewer.hint.text') }}
        </p>

        <button
          type="button"
          class="mt-3 cursor-pointer text-sm font-semibold text-primary transition-opacity hover:opacity-80"
          @click="dismissHint"
        >
          {{ t('reviewer.hint.ok') }}
        </button>
      </div>
    </Transition>

    <button
      type="button"
      class="flex h-11 min-w-11 cursor-pointer items-center justify-center gap-2 rounded-full border border-fino-border
             bg-fino-surface text-sm font-semibold text-fino-text shadow-md transition-all duration-200
             hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg active:scale-95 focus-visible:outline-2
             focus-visible:outline-primary motion-reduce:transition-none"
      :class="isLabelVisible ? 'px-3.5' : 'px-0'"
      :aria-label="t('reviewer.open')"
      :title="t('reviewer.open')"
      @click="openPanel"
    >
      <i
        class="pi pi-compass text-primary"
        aria-hidden="true"
      />

      <span
        v-if="isLabelVisible"
        class="hidden sm:inline"
      >{{ t('reviewer.open') }}</span>
    </button>
  </div>

  <Drawer
    :visible="isVisible"
    position="right"
    :header="t('reviewer.title')"
    :style="{ width: '28rem', maxWidth: '100vw' }"
    @update:visible="handleVisibleChange"
  >
    <Tabs
      v-model:value="activeTab"
      lazy
      scrollable
    >
      <TabList>
        <Tab value="scenarios">
          {{ t('reviewer.tabs.scenarios') }}
        </Tab>
        <Tab value="world">
          {{ t('reviewer.tabs.world') }}
        </Tab>
        <Tab value="why">
          {{ t('reviewer.tabs.why') }}
        </Tab>
      </TabList>

      <TabPanels>
        <TabPanel value="scenarios">
          <SandboxReviewerScenarios
            :application-id="applicationId"
            :application-inn="applicationInn"
            :application-status="applicationStatus"
            @navigated="closePanel"
          />
        </TabPanel>

        <TabPanel value="world">
          <SandboxWorldControls
            :inn="eventInn"
            :deadline-at="deadlineAt"
          />
        </TabPanel>

        <TabPanel value="why">
          <SandboxReviewerGuide />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </Drawer>
</template>
