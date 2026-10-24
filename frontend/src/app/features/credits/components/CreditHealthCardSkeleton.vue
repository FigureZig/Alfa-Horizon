<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col items-center gap-3"
    aria-busy="true"
  >
    <!-- Полукруг спидометра и балл под ним -->
    <Skeleton
      width="16rem"
      height="8rem"
      border-radius="8rem 8rem 0 0"
    />

    <Skeleton
      width="7rem"
      height="2.5rem"
    />
  </div>
</template>
