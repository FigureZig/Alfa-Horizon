<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex min-w-0 flex-col gap-5 rounded-3xl border border-fino-border
           bg-fino-surface p-5 sm:p-6"
    aria-busy="true"
  >
    <div class="flex items-center gap-3">
      <Skeleton
        width="7rem"
        height="1.5rem"
        border-radius="9999px"
      />

      <Skeleton
        width="10rem"
        height="0.875rem"
      />
    </div>

    <Skeleton
      width="60%"
      height="1.75rem"
    />

    <Skeleton
      height="12rem"
      class="sm:!h-56"
    />

    <div class="flex flex-col gap-3 border-t border-fino-border pt-4">
      <Skeleton
        width="40%"
        height="0.75rem"
      />

      <Skeleton
        v-for="index in 3"
        :key="index"
        height="1rem"
      />
    </div>
  </div>
</template>
