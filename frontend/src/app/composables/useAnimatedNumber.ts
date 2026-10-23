import { onBeforeUnmount, ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import type { Nullable } from '@/app/types/nullable'

const DEFAULT_DURATION = 300

/**
 * Число, которое перещёлкивается к новому значению, а не подменяется. При prefers-reduced-motion меняется сразу.
 */
export function useAnimatedNumber(source: MaybeRefOrGetter<Nullable<number>>, duration = DEFAULT_DURATION) {
  const displayed = ref<Nullable<number>>(toValue(source))

  let frameId = 0

  function cancelFrame() {
    cancelAnimationFrame(frameId)
  }

  function animateTo(target: Nullable<number>) {
    cancelFrame()

    const from = displayed.value
    const isInstant = from === null || target === null || window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (isInstant) {
      displayed.value = target

      return
    }

    const start: number = from
    const delta: number = target - from
    const startedAt = performance.now()

    function step(now: number) {
      const progress = Math.min((now - startedAt) / duration, 1)
      const eased = 1 - (1 - progress) ** 3

      displayed.value = start + delta * eased

      if (progress < 1) frameId = requestAnimationFrame(step)
    }

    frameId = requestAnimationFrame(step)
  }

  watch(() => toValue(source), animateTo)
  onBeforeUnmount(cancelFrame)

  return displayed
}
