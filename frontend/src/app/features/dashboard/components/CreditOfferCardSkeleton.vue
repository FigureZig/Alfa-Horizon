<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex min-w-0 flex-col gap-5 rounded-3xl border border-fino-border
           bg-fino-surface p-5 sm:p-6"
    aria-busy="true"
  >
    <Skeleton
      width="10rem"
      height="1.5rem"
      border-radius="9999px"
    />

    <div class="flex flex-col gap-3">
      <Skeleton
        width="60%"
        height="1.25rem"
      />

      <Skeleton
        width="75%"
        height="2.25rem"
      />

      <Skeleton
        width="50%"
        height="0.875rem"
      />
    </div>

    <div class="flex flex-col gap-2.5 border-t border-fino-border pt-4">
      <Skeleton
        v-for="index in 3"
        :key="index"
        height="0.875rem"
      />
    </div>

    <div class="mt-auto flex flex-col gap-2.5">
      <Skeleton
        height="3rem"
        border-radius="0.75rem"
      />

      <Skeleton
        height="3rem"
        border-radius="0.75rem"
      />
    </div>
  </div>
</template>
