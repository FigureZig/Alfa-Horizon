<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-4"
    aria-busy="true"
  >
    <div class="flex flex-wrap gap-2">
      <Skeleton
        width="7rem"
        height="1.5rem"
        border-radius="0.5rem"
      />

      <Skeleton
        width="9rem"
        height="1.5rem"
        border-radius="0.5rem"
      />

      <Skeleton
        width="3.5rem"
        height="1.5rem"
        border-radius="0.5rem"
      />

      <Skeleton
        width="8rem"
        height="1.5rem"
        border-radius="0.5rem"
      />
    </div>

    <Skeleton
      width="80%"
      height="0.75rem"
    />
  </div>
</template>
