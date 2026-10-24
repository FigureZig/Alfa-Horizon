<script setup lang="ts">
import Skeleton from 'primevue/skeleton'

const ROW_COUNT = 6
</script>

<template>
  <div
    class="overflow-hidden card-key"
    aria-busy="true"
  >
    <div
      v-for="row in ROW_COUNT"
      :key="row"
      class="flex items-center gap-4 border-b border-fino-border px-5 py-4 last:border-b-0"
    >
      <div class="min-w-0 flex-1">
        <Skeleton
          width="55%"
          height="1rem"
        />
        <Skeleton
          width="30%"
          height="0.75rem"
          class="mt-2"
        />
      </div>

      <Skeleton
        class="hidden xl:block"
        width="7rem"
        height="1rem"
      />
      <Skeleton
        class="hidden xl:block"
        width="6rem"
        height="1rem"
      />
      <Skeleton
        width="5.5rem"
        height="1.5rem"
        border-radius="9999px"
      />
    </div>
  </div>
</template>
