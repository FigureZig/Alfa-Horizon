<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div aria-busy="true">
    <Skeleton
      width="18rem"
      height="2.25rem"
      class="max-w-full"
    />

    <Skeleton
      width="12rem"
      height="1.25rem"
      class="mt-3 max-w-full"
    />

    <Skeleton
      width="9rem"
      height="1rem"
      class="mt-2 max-w-full"
    />
  </div>
</template>
