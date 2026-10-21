<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div class="flex flex-col gap-4 rounded-3xl border border-fino-border bg-fino-surface p-5">
    <div class="flex items-start justify-between gap-3">
      <Skeleton
        shape="circle"
        size="3rem"
      />

      <Skeleton
        width="2.5rem"
        height="1.5rem"
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

    <div class="border-t border-fino-border pt-4">
      <Skeleton
        width="70%"
        height="0.875rem"
      />
    </div>
  </div>
</template>
