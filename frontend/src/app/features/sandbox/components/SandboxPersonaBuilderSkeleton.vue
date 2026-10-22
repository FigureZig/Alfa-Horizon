<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-8"
    aria-busy="true"
  >
    <div
      v-for="section in 3"
      :key="section"
      class="flex flex-col gap-4"
    >
      <Skeleton
        width="30%"
        height="1.25rem"
      />

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="field in 6"
          :key="field"
          class="flex flex-col gap-2"
        >
          <Skeleton
            width="50%"
            height="0.875rem"
          />

          <Skeleton
            height="2.5rem"
            border-radius="0.75rem"
          />
        </div>
      </div>
    </div>
  </div>
</template>
