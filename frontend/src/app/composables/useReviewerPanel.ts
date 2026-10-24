import { ref } from 'vue'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxScenarioInterface } from '@/app/types/sandbox/sandbox-scenario-interface'

// Панель «Как проверить» одна на приложение: открыть её на нужном сценарии можно с любой страницы
const isVisible = ref(false)
const openScenarioId = ref<Nullable<string>>(null)

// Сценарий, который проходят сейчас, и последний выполненный шаг: по ним плашка у кнопки подсказывает,
// что сделать в кабинете и где следующий шаг — панель не нужно открывать наугад
const activeScenario = ref<Nullable<SandboxScenarioInterface>>(null)
const doneStepNumber = ref(0)

export function useReviewerPanel() {
  function openPanel(scenarioId: Nullable<string> = null) {
    if (scenarioId) openScenarioId.value = scenarioId

    isVisible.value = true
  }

  function closePanel() {
    isVisible.value = false
  }

  function markStepDone(scenario: SandboxScenarioInterface, stepNumber: number) {
    activeScenario.value = scenario
    doneStepNumber.value = stepNumber
  }

  function stopScenario() {
    activeScenario.value = null
    doneStepNumber.value = 0
  }

  return {
    isVisible,
    openScenarioId,
    activeScenario,
    doneStepNumber,
    openPanel,
    closePanel,
    markStepDone,
    stopScenario,
  }
}
