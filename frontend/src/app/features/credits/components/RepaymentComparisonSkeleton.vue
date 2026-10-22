<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-4"
    aria-busy="true"
  >
    <Skeleton
      height="2.75rem"
      border-radius="1rem"
    />

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Skeleton
        v-for="index in 2"
        :key="index"
        height="10rem"
        border-radius="1rem"
      />
    </div>
  </div>
</template>
