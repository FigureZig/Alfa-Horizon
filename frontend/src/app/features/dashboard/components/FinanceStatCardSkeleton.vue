<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div class="card-key p-5 sm:p-6">
    <div class="flex items-start justify-between gap-4">
      <Skeleton
        width="55%"
        height="0.875rem"
      />

      <Skeleton
        shape="circle"
        size="2.75rem"
      />
    </div>

    <Skeleton
      width="75%"
      height="2rem"
      class="mt-6"
    />

    <Skeleton
      width="60%"
      height="0.75rem"
      class="mt-4"
    />
  </div>
</template>
