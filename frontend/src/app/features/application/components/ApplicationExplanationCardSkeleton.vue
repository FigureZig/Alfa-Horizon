<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-5"
    aria-busy="true"
  >
    <div class="flex items-center gap-4">
      <Skeleton
        width="4rem"
        height="2.5rem"
      />

      <div class="flex flex-col gap-2">
        <Skeleton
          width="7rem"
          height="0.875rem"
        />

        <Skeleton
          width="5rem"
          height="0.75rem"
        />
      </div>
    </div>

    <div class="flex flex-col gap-3">
      <Skeleton
        v-for="index in 4"
        :key="index"
        height="1rem"
      />
    </div>
  </div>
</template>
