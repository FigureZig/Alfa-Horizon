import { ref } from 'vue'
import type { Nullable } from '@/app/types/nullable'

// Панель «Как проверить» одна на приложение: открыть её на нужном сценарии можно с любой страницы
const isVisible = ref(false)
const openScenarioId = ref<Nullable<string>>(null)

export function useReviewerPanel() {
  function openPanel(scenarioId: Nullable<string> = null) {
    if (scenarioId) openScenarioId.value = scenarioId

    isVisible.value = true
  }

  function closePanel() {
    isVisible.value = false
  }

  return { isVisible, openScenarioId, openPanel, closePanel }
}
