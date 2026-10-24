<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
import SandboxPersonaPreviewSkeleton from './SandboxPersonaPreviewSkeleton.vue'

defineProps<{
  // Правка своей компании открывается сразу результатом: предпросмотр и «Уточнить»
  isResult: boolean
}>()
</script>

<template>
  <div
    v-if="isResult"
    class="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_24rem] xl:grid-cols-[minmax(0,1fr)_28rem]"
    aria-busy="true"
  >
    <SandboxPersonaPreviewSkeleton />

    <div class="flex flex-col gap-3">
      <Skeleton
        width="40%"
        height="1.5rem"
      />

      <Skeleton
        v-for="section in 5"
        :key="section"
        height="3rem"
        border-radius="1rem"
      />
    </div>
  </div>

  <!-- Карточка вопроса интервью: прогресс, вопрос и плитки ответов -->
  <div
    v-else
    class="flex max-w-4xl flex-col gap-6 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-8"
    aria-busy="true"
  >
    <div class="flex items-center justify-between gap-3">
      <Skeleton
        width="6rem"
        height="0.875rem"
      />

      <div class="flex gap-1.5">
        <Skeleton
          v-for="step in 3"
          :key="step"
          width="2rem"
          height="0.375rem"
          border-radius="9999px"
        />
      </div>
    </div>

    <Skeleton
      width="45%"
      height="1.75rem"
    />

    <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
      <Skeleton
        v-for="tile in 16"
        :key="tile"
        height="3.5rem"
        border-radius="1rem"
      />
    </div>
  </div>
</template>
