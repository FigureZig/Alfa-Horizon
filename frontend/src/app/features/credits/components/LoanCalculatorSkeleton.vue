<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-6"
    aria-busy="true"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <Skeleton
        v-for="index in 3"
        :key="index"
        height="6.5rem"
        border-radius="1rem"
      />
    </div>

    <Skeleton
      height="12rem"
      border-radius="1rem"
    />
  </div>
</template>
