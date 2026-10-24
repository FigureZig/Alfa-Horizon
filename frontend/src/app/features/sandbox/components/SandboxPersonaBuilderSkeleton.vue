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
        height="3.75rem"
        border-radius="1rem"
      />
    </div>
  </div>

  <!-- Интервью: шаги сверху и карточка вопроса с плитками ответов -->
  <div
    v-else
    class="flex flex-col gap-6"
    aria-busy="true"
  >
    <div class="flex items-start">
      <div
        v-for="step in 4"
        :key="step"
        class="flex flex-1 flex-col items-center gap-1.5"
      >
        <Skeleton
          shape="circle"
          size="2rem"
        />
        <Skeleton
          width="5rem"
          height="0.75rem"
          class="hidden sm:block"
        />
      </div>
    </div>

    <div class="flex flex-col gap-6 card-key p-5 sm:p-8 lg:p-10">
      <div class="flex flex-col gap-2">
        <Skeleton
          width="6rem"
          height="0.875rem"
        />
        <Skeleton
          width="45%"
          height="2rem"
        />
        <Skeleton
          width="70%"
          height="1rem"
        />
      </div>

      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <Skeleton
          v-for="tile in 16"
          :key="tile"
          height="4rem"
          border-radius="1rem"
        />
      </div>
    </div>
  </div>
</template>
