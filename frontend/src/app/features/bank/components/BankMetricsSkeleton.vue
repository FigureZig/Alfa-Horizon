<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-6"
    aria-busy="true"
  >
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Skeleton
        v-for="index in 4"
        :key="index"
        height="8rem"
        border-radius="1.5rem"
      />
    </div>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Skeleton
        v-for="index in 2"
        :key="index"
        height="11rem"
        border-radius="1.5rem"
      />
    </div>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Skeleton
        v-for="index in 2"
        :key="index"
        height="14rem"
        border-radius="1.5rem"
      />
    </div>
  </div>
</template>
