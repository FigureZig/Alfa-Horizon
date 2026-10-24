<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div class="flex flex-col gap-4 card-key p-6">
    <div class="flex items-start justify-between gap-3">
      <Skeleton
        width="50%"
        height="1.25rem"
      />
      <Skeleton
        width="6rem"
        height="1.5rem"
        border-radius="9999px"
      />
    </div>

    <Skeleton
      width="45%"
      height="2rem"
    />

    <Skeleton
      height="0.5rem"
      border-radius="9999px"
    />

    <Skeleton
      width="60%"
      height="0.875rem"
    />
  </div>
</template>
