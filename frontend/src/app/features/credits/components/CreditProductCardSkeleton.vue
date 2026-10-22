<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-4 rounded-3xl border border-fino-border bg-fino-surface p-5"
    aria-busy="true"
  >
    <div class="flex items-start justify-between gap-3">
      <Skeleton
        width="50%"
        height="1.25rem"
      />

      <Skeleton
        width="4.5rem"
        height="1.75rem"
        border-radius="0.5rem"
      />
    </div>

    <div class="grid grid-cols-2 gap-3">
      <Skeleton height="2.5rem" />

      <Skeleton height="2.5rem" />
    </div>

    <div class="flex flex-col gap-2">
      <Skeleton
        v-for="index in 3"
        :key="index"
        height="0.875rem"
      />
    </div>

    <div class="grid grid-cols-2 gap-2">
      <Skeleton
        height="2.75rem"
        border-radius="0.75rem"
      />

      <Skeleton
        height="2.75rem"
        border-radius="0.75rem"
      />
    </div>
  </div>
</template>
