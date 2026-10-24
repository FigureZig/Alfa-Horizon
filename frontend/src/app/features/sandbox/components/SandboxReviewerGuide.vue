<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const ROWS = [
  { key: 'company', icon: 'pi pi-building' },
  { key: 'decision', icon: 'pi pi-question-circle' },
  { key: 'forecast', icon: 'pi pi-chart-line' },
  { key: 'data', icon: 'pi pi-database' },
  { key: 'history', icon: 'pi pi-history' },
] as const

const README_URL = 'https://github.com/FigureZig/Alfa-Horizon#readme'

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div class="flex flex-col gap-5">
    <p class="text-sm leading-relaxed text-fino-text-muted">
      {{ t('reviewer.guide.description') }}
    </p>

    <ul class="flex flex-col gap-3">
      <li
        v-for="row in ROWS"
        :key="row.key"
        class="flex items-start gap-3 rounded-2xl border border-fino-border bg-fino-surface p-3"
      >
        <span class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-fino-accent text-primary border-2 border-fino-line">
          <i
            :class="row.icon"
            aria-hidden="true"
          />
        </span>

        <div class="min-w-0">
          <p class="text-sm font-semibold text-fino-text">
            {{ t(`reviewer.guide.rows.${row.key}.what`) }}
          </p>
          <p class="mt-0.5 text-xs leading-relaxed text-fino-text-muted">
            {{ t(`reviewer.guide.rows.${row.key}.where`) }}
          </p>
        </div>
      </li>
    </ul>

    <div class="flex flex-wrap gap-2">
      <a
        :href="README_URL"
        target="_blank"
        rel="noopener"
        class="inline-flex min-h-10 items-center gap-2 rounded-xl border border-fino-border px-4 text-sm font-semibold
               text-fino-text transition-colors hover:bg-fino-surface-hover motion-reduce:transition-none"
      >
        <i
          class="pi pi-book text-xs"
          aria-hidden="true"
        />
        {{ t('reviewer.guide.readme') }}
      </a>
    </div>
  </div>
</template>
