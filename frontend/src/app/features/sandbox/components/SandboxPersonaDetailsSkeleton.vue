<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-6 rounded-3xl border border-fino-border
           bg-fino-surface p-5 sm:p-6"
  >
    <div class="flex items-center gap-4">
      <Skeleton
        shape="circle"
        size="3.5rem"
      />

      <div class="flex-1">
        <Skeleton
          width="60%"
          height="1.5rem"
        />

        <Skeleton
          width="80%"
          height="0.875rem"
          class="mt-2"
        />
      </div>
    </div>

    <div class="flex flex-col divide-y divide-fino-border">
      <div
        v-for="index in 5"
        :key="index"
        class="py-4 first:pt-0 last:pb-0"
      >
        <Skeleton
          width="30%"
          height="0.75rem"
        />

        <Skeleton
          width="90%"
          height="0.875rem"
          class="mt-2"
        />
      </div>
    </div>

    <div class="flex flex-col gap-3">
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
