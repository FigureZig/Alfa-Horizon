<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-5"
    aria-busy="true"
  >
    <div class="flex flex-col gap-3">
      <Skeleton
        v-for="index in 6"
        :key="index"
        height="1rem"
      />
    </div>

    <div class="flex flex-col gap-3">
      <Skeleton
        width="35%"
        height="0.75rem"
      />

      <Skeleton
        v-for="index in 6"
        :key="index"
        height="1rem"
      />
    </div>
  </div>
</template>
