<script setup lang="ts">
import { onBeforeUnmount, onMounted, useTemplateRef } from 'vue'

// Фон из точек, которые разъезжаются из-под курсора и пружиной возвращаются на место
const SPACING = 14
const DOT_RADIUS = 1.6
const PUSH_RADIUS = 120
const PUSH_STRENGTH = 26
const SPRING = 0.16
const REST_THRESHOLD = 0.05

const canvas = useTemplateRef<HTMLCanvasElement>('canvas')

let context: CanvasRenderingContext2D | null = null
let columns = 0
let rows = 0
let offsetX = new Float32Array(0)
let offsetY = new Float32Array(0)
let pointer: { x: number, y: number } | null = null
let frame = 0
let isReducedMotion = false

function resize() {
  const element = canvas.value

  if (!element) return

  const ratio = window.devicePixelRatio || 1

  element.width = window.innerWidth * ratio
  element.height = window.innerHeight * ratio
  context = element.getContext('2d')
  context?.setTransform(ratio, 0, 0, ratio, 0, 0)

  columns = Math.ceil(window.innerWidth / SPACING) + 1
  rows = Math.ceil(window.innerHeight / SPACING) + 1
  offsetX = new Float32Array(columns * rows)
  offsetY = new Float32Array(columns * rows)

  draw()
}

// Цвет точек берём из темы при каждой отрисовке: при смене темы фон перекрашивается сам
function draw() {
  if (!context) return

  context.clearRect(0, 0, window.innerWidth, window.innerHeight)
  context.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--fino-grid').trim()
  context.beginPath()

  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const index = row * columns + column
      const x = column * SPACING + offsetX[index]
      const y = row * SPACING + offsetY[index]

      context.moveTo(x + DOT_RADIUS, y)
      context.arc(x, y, DOT_RADIUS, 0, Math.PI * 2)
    }
  }

  context.fill()
}

// Шаг физики: точка тянется к позиции «отталкивания» от курсора; без курсора — обратно домой
function step() {
  let isMoving = false

  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const index = row * columns + column
      let targetX = 0
      let targetY = 0

      if (pointer) {
        const dx = column * SPACING - pointer.x
        const dy = row * SPACING - pointer.y
        const distance = Math.hypot(dx, dy)

        if (distance < PUSH_RADIUS && distance > 0) {
          const force = (1 - distance / PUSH_RADIUS) ** 2 * PUSH_STRENGTH

          targetX = (dx / distance) * force
          targetY = (dy / distance) * force
        }
      }

      offsetX[index] += (targetX - offsetX[index]) * SPRING
      offsetY[index] += (targetY - offsetY[index]) * SPRING

      if (Math.abs(targetX - offsetX[index]) > REST_THRESHOLD || Math.abs(targetY - offsetY[index]) > REST_THRESHOLD) {
        isMoving = true
      }
    }
  }

  draw()

  // Всё успокоилось — кадры не крутим, пока курсор снова не сдвинется
  frame = isMoving ? requestAnimationFrame(step) : 0
}

function wake() {
  if (!frame) frame = requestAnimationFrame(step)
}

function handlePointerMove(event: PointerEvent) {
  pointer = { x: event.clientX, y: event.clientY }
  wake()
}

function handlePointerLeave() {
  pointer = null
  wake()
}

// Смена темы: перерисовать точки новым цветом
const themeObserver = new MutationObserver(draw)

onMounted(() => {
  isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  resize()
  window.addEventListener('resize', resize)
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })

  if (!isReducedMotion) {
    window.addEventListener('pointermove', handlePointerMove, { passive: true })
    document.documentElement.addEventListener('pointerleave', handlePointerLeave)
  }
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  themeObserver.disconnect()
  window.removeEventListener('resize', resize)
  window.removeEventListener('pointermove', handlePointerMove)
  document.documentElement.removeEventListener('pointerleave', handlePointerLeave)
})
</script>

<template>
  <canvas
    ref="canvas"
    class="pointer-events-none fixed inset-0 -z-10 size-full"
    aria-hidden="true"
  />
</template>
