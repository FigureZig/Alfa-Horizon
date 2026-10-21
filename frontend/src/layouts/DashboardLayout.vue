<script setup lang="ts">
import AppHeader from '@/app/components/layout/AppHeader.vue'
import AppSidebar from '@/app/components/layout/AppSidebar.vue'
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader />

    <div
      class="mx-auto flex max-w-[1600px] items-start
             gap-6 px-4 pt-6
             pb-[calc(7rem+env(safe-area-inset-bottom))]
             sm:px-6 lg:pb-6"
    >
      <AppSidebar />

      <main class="min-w-0 flex-1">
        <RouterView />
      </main>
    </div>
  </div>
</template>