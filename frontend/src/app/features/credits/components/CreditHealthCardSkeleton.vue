<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex flex-col gap-5"
    aria-busy="true"
  >
    <div class="flex items-center gap-4">
      <Skeleton
        width="5rem"
        height="3rem"
      />

      <div class="flex flex-col gap-2">
        <Skeleton
          width="6rem"
          height="1.5rem"
          border-radius="0.5rem"
        />

        <Skeleton
          width="4rem"
          height="0.75rem"
        />
      </div>
    </div>

    <div class="grid grid-cols-4 gap-2">
      <Skeleton
        v-for="index in 4"
        :key="index"
        height="3rem"
        border-radius="0.75rem"
      />
    </div>

    <div class="flex flex-col gap-3">
      <Skeleton
        v-for="index in 5"
        :key="index"
        height="1.25rem"
      />
    </div>
  </div>
</template>
