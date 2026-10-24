<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div class="flex flex-col gap-5 card-key p-6">
    <div class="flex items-start justify-between gap-3">
      <Skeleton
        width="55%"
        height="1.25rem"
      />
      <Skeleton
        width="4.5rem"
        height="1.5rem"
        border-radius="9999px"
      />
    </div>

    <Skeleton
      width="75%"
      height="2rem"
    />

    <div class="flex flex-col gap-2">
      <Skeleton height="0.875rem" />
      <Skeleton
        width="85%"
        height="0.875rem"
      />
    </div>

    <div class="flex flex-col gap-2 border-t border-fino-border pt-4">
      <Skeleton
        width="70%"
        height="0.875rem"
      />
      <Skeleton
        width="60%"
        height="0.875rem"
      />
    </div>
  </div>
</template>
