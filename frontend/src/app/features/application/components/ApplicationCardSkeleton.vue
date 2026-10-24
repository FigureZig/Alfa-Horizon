<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div class="flex flex-col gap-4 card-key p-5">
    <div class="flex items-start justify-between gap-3">
      <Skeleton
        width="55%"
        height="1.25rem"
      />

      <Skeleton
        width="5rem"
        height="1.5rem"
        border-radius="0.5rem"
      />
    </div>

    <div class="flex flex-col gap-2">
      <Skeleton
        width="45%"
        height="2rem"
      />

      <Skeleton
        width="30%"
        height="0.875rem"
      />
    </div>

    <Skeleton
      width="60%"
      height="0.75rem"
      class="mt-2"
    />
  </div>
</template>
