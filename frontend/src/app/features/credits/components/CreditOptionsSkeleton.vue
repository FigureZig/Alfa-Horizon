<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-4"
    aria-busy="true"
  >
    <div class="rounded-3xl border border-fino-border bg-fino-surface p-6">
      <Skeleton
        width="45%"
        height="1.5rem"
      />
      <Skeleton
        width="60%"
        height="2.5rem"
        class="mt-4"
      />
      <Skeleton
        width="50%"
        height="0.875rem"
        class="mt-3"
      />
      <Skeleton
        width="9rem"
        height="2.75rem"
        border-radius="0.75rem"
        class="mt-5"
      />
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div
        v-for="index in 2"
        :key="index"
        class="rounded-3xl border border-fino-border bg-fino-surface p-5"
      >
        <Skeleton
          width="55%"
          height="1.25rem"
        />
        <Skeleton
          width="40%"
          height="1.75rem"
          class="mt-4"
        />
        <Skeleton
          width="9rem"
          height="2.75rem"
          border-radius="0.75rem"
          class="mt-4"
        />
      </div>
    </div>
  </div>
</template>
