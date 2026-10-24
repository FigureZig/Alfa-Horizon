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
import SandboxScenarioTracker from './SandboxScenarioTracker.vue'
import SandboxWorldControls from './SandboxWorldControls.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useReviewerPanel } from '@/app/composables/useReviewerPanel'
import { useScenarioRun } from '@/app/composables/useScenarioRun'
import { applicationsService } from '@/app/services/application/applications.service'
import { ApplicationMapper } from '@/app/mappers/application.mapper'
import type { Nullable } from '@/app/types/nullable'


const { t } = useI18n({ useScope: 'global' })
const route = useRoute()
const $fetch = useApiFetch()
const { isVisible, openScenarioId, openPanel: showPanel, closePanel } = useReviewerPanel()
const { scenario: activeScenario } = useScenarioRun()

const activeTab = ref('scenarios')
// Срок текущего шага заявки на экране: к нему можно перемотать время мира
const deadlineAt = ref<Nullable<string>>(null)

const applicationId = computed(() => (typeof route.params.applicationId === 'string' ? route.params.applicationId : null))
const inn = computed(() => (typeof route.params.inn === 'string' ? route.params.inn : undefined))

// События и отказы относятся к компании клиента; на рабочем месте банка ИНН компании подставлять не из чего
const eventInn = computed(() => (route.meta.area === 'bank' ? undefined : inn.value))

// В кабинете снизу мобильная навигация: кнопка стоит над ней
const positionClass = computed(() => {
  // В конструкторе снизу полоса предпросмотра
  if (route.name === 'login-company' || route.name === 'login-company-edit') return 'bottom-24 lg:bottom-6'

  return inn.value ? 'bottom-24 lg:bottom-6' : 'bottom-4 sm:bottom-6'
})

// Идёт сценарий — панель открывается сразу на нём
function openPanel() {
  showPanel(activeScenario.value?.id ?? null)
}

function handleVisibleChange(visible: boolean) {
  isVisible.value = visible
}

// Срок текущего шага открытой заявки — для перемотки времени во вкладке «Мир»; чужая заявка (403) пропускается
async function loadApplicationStatus() {
  deadlineAt.value = null

  if (!applicationId.value) return

  try {
    const { data } = await applicationsService.fetchApplication($fetch, applicationId.value)
    const application = ApplicationMapper.toEntity(data.data)

    deadlineAt.value = application.deadline?.status === application.status ? application.deadline.at : null
  } catch (err: unknown) {
    console.error('Reviewer application status loading failed:', err)
  }
}

watch([isVisible, applicationId], ([visible]) => {
  if (visible) loadApplicationStatus()
})

// Открыли на конкретном сценарии (например, с экрана входа) — показываем вкладку сценариев
watch(openScenarioId, (scenarioId) => {
  if (scenarioId) activeTab.value = 'scenarios'
})
</script>

<template>
  <div
    class="fixed right-4 z-40 flex items-end gap-2 sm:right-6 sm:flex-col sm:gap-3"
    :class="positionClass"
  >
    <!-- Идёт сценарий: что сделать сейчас и кнопка следующего шага -->
    <Transition
      enter-active-class="transition duration-300 ease-out motion-reduce:transition-none"
      enter-from-class="translate-y-4 opacity-0"
      leave-active-class="transition duration-150 ease-in motion-reduce:transition-none"
      leave-to-class="opacity-0"
    >
      <SandboxScenarioTracker v-if="!isVisible" />
    </Transition>

    <button
      type="button"
      class="flex h-12 min-w-12 cursor-pointer items-center justify-center gap-2 rounded-2xl bg-fino-violet
             font-display text-base font-extrabold text-white btn-key focus-visible:outline-2
             focus-visible:outline-primary sm:px-4"
      :aria-label="t('reviewer.open')"
      :title="t('reviewer.open')"
      @click="openPanel"
    >
      <i
        class="pi pi-compass"
        aria-hidden="true"
      />

      <span class="hidden sm:inline">{{ t('reviewer.open') }}</span>
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
          <SandboxReviewerScenarios @navigated="closePanel" />
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
