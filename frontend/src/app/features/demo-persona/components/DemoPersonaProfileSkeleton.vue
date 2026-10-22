<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex items-center gap-3 sm:border-l sm:border-fino-border sm:pl-3"
    aria-busy="true"
  >
    <Skeleton
      shape="circle"
      size="2.5rem"
    />

    <div class="hidden flex-col gap-1.5 md:flex">
      <Skeleton
        width="8rem"
        height="0.875rem"
      />

      <Skeleton
        width="5rem"
        height="0.75rem"
      />
    </div>
  </div>
</template>
