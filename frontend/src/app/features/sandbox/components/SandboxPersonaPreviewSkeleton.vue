<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-4"
    aria-busy="true"
  >
    <div class="rounded-3xl border border-fino-border bg-fino-surface p-5">
      <Skeleton
        width="35%"
        height="0.75rem"
      />
      <Skeleton
        width="70%"
        height="1.5rem"
        class="mt-2"
      />
      <Skeleton
        height="0.875rem"
        class="mt-3"
      />
    </div>

    <div class="rounded-3xl border border-fino-border bg-fino-surface p-5">
      <Skeleton
        width="40%"
        height="1rem"
      />

      <div class="mt-3 flex flex-col gap-2">
        <Skeleton
          v-for="index in 6"
          :key="index"
          height="3.5rem"
          border-radius="1rem"
        />
      </div>
    </div>

    <div class="flex items-center gap-5 rounded-3xl border border-fino-border bg-fino-surface p-5">
      <Skeleton
        width="3rem"
        height="3.5rem"
      />
      <Skeleton
        class="flex-1"
        height="0.75rem"
      />
    </div>
  </div>
</template>
