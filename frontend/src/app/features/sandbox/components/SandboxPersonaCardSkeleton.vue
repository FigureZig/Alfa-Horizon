<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div class="flex flex-col gap-4 rounded-3xl border border-fino-border bg-fino-surface p-5">
    <div class="flex items-start justify-between gap-3">
      <Skeleton
        width="3rem"
        height="3rem"
        border-radius="1rem"
      />

      <Skeleton
        width="4.5rem"
        height="1.5rem"
        border-radius="9999px"
      />
    </div>

    <div>
      <Skeleton
        width="60%"
        height="1.25rem"
      />

      <Skeleton
        width="80%"
        height="0.875rem"
        class="mt-2"
      />
    </div>

    <div class="flex flex-col gap-2">
      <Skeleton height="0.75rem" />
      <Skeleton
        width="85%"
        height="0.75rem"
      />
    </div>

    <Skeleton
      height="2.75rem"
      border-radius="0.75rem"
    />
  </div>
</template>
