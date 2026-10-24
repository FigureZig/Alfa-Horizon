<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div
    class="flex min-w-0 flex-col gap-6"
    aria-busy="true"
  >
    <div class="flex flex-col gap-3">
      <Skeleton
        width="8rem"
        height="0.875rem"
      />

      <Skeleton
        width="50%"
        height="2rem"
        class="max-w-full"
      />

      <Skeleton
        width="30%"
        height="1rem"
        class="max-w-full"
      />
    </div>

    <div class="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <div class="flex flex-col gap-5 card-key p-5 sm:p-6">
        <Skeleton height="2rem" />

        <Skeleton
          height="9rem"
          border-radius="1rem"
        />

        <Skeleton
          width="40%"
          height="3rem"
          border-radius="0.75rem"
        />
      </div>

      <div class="flex flex-col gap-4 card-key p-5">
        <Skeleton
          v-for="index in 4"
          :key="index"
          height="1.5rem"
        />
      </div>
    </div>
  </div>
</template>
