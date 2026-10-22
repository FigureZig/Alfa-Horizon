<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="grid gap-6 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]"
    aria-busy="true"
  >
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
      <div
        v-for="index in 4"
        :key="index"
        class="rounded-2xl border border-fino-border bg-fino-surface p-5"
      >
        <Skeleton
          width="75%"
          height="1.25rem"
        />
        <Skeleton
          width="55%"
          height="0.875rem"
          class="mt-3"
        />
      </div>
    </div>
    <div class="rounded-2xl border border-fino-border bg-fino-surface p-6">
      <Skeleton
        width="65%"
        height="1.75rem"
      />
      <Skeleton
        width="90%"
        height="0.875rem"
        class="mt-4"
      />
      <Skeleton
        v-for="index in 4"
        :key="index"
        width="100%"
        height="4.5rem"
        class="mt-4"
      />
    </div>
  </div>
</template>
