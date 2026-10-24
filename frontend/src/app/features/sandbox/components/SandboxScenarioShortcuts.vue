<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import SandboxScenarioShortcutsSkeleton from './SandboxScenarioShortcutsSkeleton.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useReviewerPanel } from '@/app/composables/useReviewerPanel'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxScenarioMapper } from '@/app/mappers/sandbox-scenario.mapper'
import type { AppLocale } from '@/app/i18n'
import type { SandboxScenarioInterface } from '@/app/types/sandbox/sandbox-scenario-interface'

const { t, locale } = useI18n({ useScope: 'global' })
const $fetch = useApiFetch()
const { openPanel } = useReviewerPanel()

const scenarios = ref<SandboxScenarioInterface[]>([])
const isLoading = ref(false)
const hasError = ref(false)

// На карточке — кто по очереди входит: имена без повторов в порядке шагов
const cards = computed(() =>
  scenarios.value.map((scenario) => ({
    scenario,
    people: [...new Set(scenario.steps.flatMap((step) => (step.user ? [step.user.fullName] : [])))].join(' → '),
  })),
)

async function loadScenarios() {
  if (isLoading.value) return

  isLoading.value = true
  hasError.value = false

  try {
    const { data } = await sandboxService.fetchScenarios($fetch, locale.value as AppLocale)

    scenarios.value = data.data.map((scenario) => SandboxScenarioMapper.toEntity(scenario))
  } catch (err: unknown) {
    console.error('Login scenarios loading failed:', err)
    hasError.value = true
  } finally {
    isLoading.value = false
  }
}

// Шаги, входы и ожидаемые статусы живут в панели «Как проверить» — открываем её на этом сценарии
function startScenario(scenario: SandboxScenarioInterface) {
  openPanel(scenario.id)
}

onMounted(loadScenarios)
watch(locale, loadScenarios)
</script>

<template>
  <section
    class="flex flex-col gap-4"
    aria-labelledby="login-scenarios-title"
  >
    <div class="flex flex-col gap-1">
      <h2
        id="login-scenarios-title"
        class="text-xl font-bold tracking-tight text-fino-text"
      >
        {{ t('login.scenarios.title') }}
      </h2>

      <p class="text-sm leading-relaxed text-fino-text-muted">
        {{ t('login.scenarios.description') }}
      </p>
    </div>

    <SandboxScenarioShortcutsSkeleton v-if="isLoading && !scenarios.length" />

    <AppErrorState
      v-else-if="hasError"
      :message="t('sandbox.scenarios.loadError')"
      is-inline
      @retry="loadScenarios"
    />

    <ul
      v-else-if="scenarios.length"
      class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
    >
      <li
        v-for="card in cards"
        :key="card.scenario.id"
      >
        <button
          type="button"
          class="group flex h-full w-full cursor-pointer flex-col gap-2 rounded-2xl border border-fino-border
                 bg-fino-surface p-4 text-left transition-[border-color,box-shadow] duration-200
                 hover:border-primary/40 hover:shadow-md focus-visible:outline-2 focus-visible:outline-primary
                 motion-reduce:transition-none"
          @click="startScenario(card.scenario)"
        >
          <span class="break-words text-sm font-bold text-fino-text">{{ card.scenario.title }}</span>

          <span class="break-words text-xs text-fino-text-muted">
            {{ t('login.scenarios.steps', card.scenario.steps.length) }} · {{ card.scenario.company.name }}
          </span>

          <span
            v-if="card.people"
            class="line-clamp-2 break-words text-xs text-fino-text-muted"
          >
            {{ card.people }}
          </span>

          <span class="mt-auto inline-flex items-center gap-1.5 pt-1 text-sm font-semibold text-primary">
            {{ t('login.scenarios.start') }}
            <i
              class="pi pi-arrow-right text-xs transition-transform duration-200 group-hover:translate-x-0.5
                     motion-reduce:transition-none"
              aria-hidden="true"
            />
          </span>
        </button>
      </li>
    </ul>
  </section>
</template>
