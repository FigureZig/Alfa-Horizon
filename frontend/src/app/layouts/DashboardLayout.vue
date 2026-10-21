<script setup lang="ts">
import AppHeader from '@/app/components/layout/AppHeader.vue'
import AppSidebar from '@/app/components/layout/AppSidebar.vue'
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader />

    <div
      class="mx-auto flex max-w-[1600px] items-start
             gap-6 px-4 py-6 sm:px-6"
    >
      <AppSidebar class="sticky top-28 hidden lg:block" />

      <main class="min-w-0 flex-1">
        <RouterView />
      </main>
    </div>
  </div>
</template>