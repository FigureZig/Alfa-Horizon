<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-4 rounded-3xl border border-fino-border bg-fino-surface p-5"
    aria-busy="true"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="flex min-w-0 flex-1 flex-col gap-2">
        <Skeleton
          width="60%"
          height="1.25rem"
        />

        <Skeleton
          width="35%"
          height="0.75rem"
        />
      </div>

      <Skeleton
        width="6rem"
        height="1.5rem"
        border-radius="0.5rem"
      />
    </div>

    <div class="flex flex-col gap-2">
      <Skeleton
        width="75%"
        height="1rem"
      />

      <Skeleton
        width="55%"
        height="0.75rem"
      />
    </div>

    <Skeleton
      height="2.25rem"
      border-radius="0.75rem"
    />

    <Skeleton
      width="40%"
      height="1rem"
      class="mt-2"
    />
  </div>
</template>
