<script setup lang="ts">
import Skeleton from 'primevue/skeleton'

const CARD_COUNT = 6
</script>

<template>
  <div
    class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
    aria-busy="true"
  >
    <div
      v-for="index in CARD_COUNT"
      :key="index"
      class="flex flex-col gap-2 rounded-2xl border border-fino-border bg-fino-surface p-4"
    >
      <Skeleton
        width="70%"
        height="1rem"
      />
      <Skeleton
        width="50%"
        height="0.75rem"
      />
      <Skeleton
        width="85%"
        height="0.75rem"
      />
      <Skeleton
        width="6rem"
        height="1rem"
        class="mt-2"
      />
    </div>
  </div>
</template>
