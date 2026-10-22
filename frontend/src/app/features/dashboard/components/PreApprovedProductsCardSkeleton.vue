<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col divide-y divide-fino-border"
    aria-busy="true"
  >
    <div
      v-for="index in 2"
      :key="index"
      class="flex items-center gap-3 py-3 first:pt-0 last:pb-0"
    >
      <div class="flex min-w-0 flex-1 flex-col gap-1.5">
        <Skeleton
          width="50%"
          height="0.875rem"
        />

        <Skeleton
          width="70%"
          height="0.75rem"
        />
      </div>

      <Skeleton
        width="5rem"
        height="1.875rem"
        border-radius="0.5rem"
      />
    </div>
  </div>
</template>
