<script setup lang="ts">
import Toast from 'primevue/toast'
import SandboxReviewerPanel from '@/app/features/sandbox/components/SandboxReviewerPanel.vue'
</script>

<template>
  <Toast position="top-right" />
  <RouterView />
  <SandboxReviewerPanel />
</template>