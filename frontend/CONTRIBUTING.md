# Fino Frontend — Development Rules

Как устроен и как пишется фронтенд: стиль, структура, компоненты, типы, сервисы. Общие правила репозитория — в [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

## 1. Styling and Design

1. Prioritize Tailwind CSS utility classes.
2. Avoid `<style scoped>` and separate component CSS files whenever possible.
3. Use PrimeVue for complex interactive UI elements, including dialogs, forms, dropdowns, notifications, drawers, and skeletons.
4. Use Tailwind CSS for grids, cards, spacing, typography, responsiveness, transitions, and animations.
5. Maintain a consistent Fino visual style. Extract repeated visual patterns into shared styles or components when doing so meaningfully improves consistency.
6. Do not introduce new colors or CSS variables unless necessary.
7. Use the existing palette in `src/theme/palette.css`.
8. Use PrimeIcons (`pi pi-*`) exclusively.
9. Keep the interface modern, clean, professional, and user-friendly.
10. Account for both light and dark themes in every component state.

## 2. Responsive Design

1. Follow a mobile-first approach.
2. Use standard Tailwind CSS breakpoints.
3. Prevent unintended horizontal scrolling caused by layout issues.
4. Keep all essential functionality accessible on mobile devices.
5. Limit the main desktop container to a maximum width of `1600px`.
6. Never hide important functionality on mobile without providing an alternative way to access it.
7. Account for long translations, loading states, and errors on narrow screens.

## 3. Project Architecture

The main application code lives under `src/app/`. Preserve the existing structure:

- `src/app/pages/` — application pages.
- `src/app/components/` — shared reusable components.
- `src/app/features/` — feature-specific components and logic.
- `src/app/composables/` — reusable reactive logic.
- `src/app/services/` — API HTTP requests.
- `src/app/mappers/` — DTO-to-entity and entity-to-payload transformations.
- `src/app/schemas/` — Zod validation schemas, where needed.
- `src/app/mocks/` — mock data.
- `src/app/types/` — TypeScript interfaces, DTOs, and shared types.

### Code Organization Rules

1. Do not create unnecessary files or directories.
2. Do not extract simple logic into a composable without a clear reason.
3. Avoid unnecessary abstractions and overcomplicating small components.
4. Reuse existing components before creating new ones.
5. Follow existing naming conventions and import patterns.
6. Use the `@/app/` alias for application imports.
7. Do not change working architecture without a clear need.

**Prefer simple, readable solutions over complex, overly generic implementations.**

## 4. Vue Component Rules

### Component Structure

1. Use Vue 3 Composition API.
2. Every `.vue` component must include `<script setup lang="ts">`, even if it currently has no JavaScript logic.
3. Keep blocks in this order: `<script setup lang="ts">`, `<template>`, then `<style scoped>` only when necessary.
4. Do not use Options API.
5. Do not add unnecessary variables, functions, or imports.

### Functions and Event Handlers

1. Extract event handlers into named functions inside `<script setup>`.
2. Do not write arrow functions or assignments directly in templates.
3. Keep complex expressions and business logic out of `<template>`.
4. Reference previously declared functions from templates.
5. Use clear, descriptive function names.
6. Use `computed` for derived values instead of unnecessary functions.
7. Prefer `useToggle` from `@vueuse/core` for boolean state when the dependency is available.

**Correct:**

```vue
<script setup lang="ts">
import { useToggle } from '@vueuse/core'

const [isOpen, toggleMenu] = useToggle(false)

function openMenu() {
  toggleMenu(true)
}

function closeMenu() {
  toggleMenu(false)
}
</script>

<template>
  <button @click="openMenu">Open</button>
  <button @click="closeMenu">Close</button>
</template>
```

**Incorrect:**

```vue
<template>
  <button @click="() => isOpen = true">Open</button>
  <button @click="isOpen = false">Close</button>
</template>
```

### Events (Emits)

1. Declare events with TypeScript-typed `defineEmits`.
2. Use event names that clearly describe the action.
3. Do not declare `defineEmits` in components that emit no events.
4. Do not declare unused events.
5. Use props and emits for parent-child communication instead of directly modifying parent state.
6. Explicitly type event payloads.
7. Extract child-event handlers into named functions in the parent component.
8. For nullable values, use the shared `Nullable<T>` type from `@/app/types/nullable`; do not write `T | null` directly.

**Child component (`ChildComponent.vue`):**

```vue
<script setup lang="ts">
const emit = defineEmits<{
  close: []
  select: [id: number]
}>()

function handleClose() {
  emit('close')
}

function handleSelect() {
  emit('select', 1)
}
</script>

<template>
  <button @click="handleClose">Close</button>
  <button @click="handleSelect">Select</button>
</template>
```

**Parent component:**

```vue
<script setup lang="ts">
import { ref } from 'vue'
import ChildComponent from './ChildComponent.vue'
import type { Nullable } from '@/app/types/nullable'

const selectedId = ref<Nullable<number>>(null)
const isOpen = ref(true)

function handleSelect(id: number) {
  selectedId.value = id
}

function handleClose() {
  isOpen.value = false
}
</script>

<template>
  <ChildComponent
    v-if="isOpen"
    @select="handleSelect"
    @close="handleClose"
  />
</template>
```

**Incorrect:**

```vue
<script setup lang="ts">
import { ref } from 'vue'

const selectedId = ref<number | null>(null)
</script>

<template>
  <ChildComponent @select="(id) => selectedId = id" />
</template>
```

**Correct:** use `Nullable<T>` for nullable state and named event handlers.

### Props

1. Declare props with TypeScript-typed `defineProps`.
2. Do not use `any`.
3. Never mutate props directly inside a child component.
4. Use `computed` for derived values.
5. Use emits to notify parents about changes.

## 5. Localization

1. Use the existing Vue I18n setup.
2. Add every new user-facing string to both `ru.ts` and `en.ts`.
3. Do not hardcode user-facing interface strings.
4. Preserve the existing language-switching behavior.
5. Verify that Russian and English strings fit within the interface.
6. Localize notifications, error messages, empty states, and action labels.

## 6. Code Quality

1. Use TypeScript and explicit types where useful.
2. Avoid `any`; use `unknown` for untrusted data.
3. Use `computed` for derived values.
4. Use props and emits for component communication.
5. Do not duplicate business logic.
6. Do not rewrite working code unnecessarily.
7. Do not add unnecessary dependencies.
8. Avoid premature optimization.
9. Write clean, readable, maintainable code.

## 7. TypeScript Types and Interfaces

### Naming Conventions

1. Use `interface` for client-side entity structures and DTOs.
2. Use `type` for unions, aliases, and utility types.
3. Use `enum` for fixed sets of values, such as statuses, roles, and transaction types.
4. Client-side interface names must end with `Interface`, e.g. `DashboardStatisticInterface`.
5. DTO names must end with `Dto`, e.g. `DashboardStatisticsDto`.
6. Enum names must end with `Enum`, e.g. `ApplicationStatusEnum`.
7. Use PascalCase for type, interface, and enum names.
8. Use kebab-case for type filenames: `dashboard-statistic-interface.ts`, `dashboard-statistics-dto.ts`, `application-status-enum.ts`.
9. Keep client interfaces, DTOs, and enums in separate files.
10. Use camelCase for client-side entity properties.
11. Preserve API contract field names in DTOs, including snake_case.
12. Prefer string enums whose values match the API contract. Do not use magic strings when a suitable enum already exists.
13. Use `import type` for type-only imports. Use regular `import` for enums needed at runtime.
14. Do not use `any`; prefer `unknown` for raw external data.
15. Reuse shared types instead of duplicating them, including `Nullable<T>` for nullable values.

### Client-Side Interface

File: `src/app/types/dashboard/dashboard-statistic-interface.ts`

```ts
export interface DashboardStatisticInterface {
  balance: number
  income: number
  expenses: number
  activeCredits: number
}
```

### Backend DTO

File: `src/app/types/dashboard/dashboard-statistics-dto.ts`

```ts
export interface DashboardStatisticsDto {
  total_balance: number
  monthly_income: number
  monthly_expenses: number
  active_loans_count: number
}
```

Do not use a backend DTO as the primary Vue component model when a client-side entity exists.

### Shared Types

File: `src/app/types/nullable.ts`

```ts
export type Nullable<T> = T | null
```

Usage:

```ts
const dashboard = ref<Nullable<DashboardStatisticInterface>>(null)
```

File: `src/app/types/api-response.ts`

```ts
export interface ApiResponse<T = null> {
  data: T
}
```

Example: `ApiResponse<DashboardStatisticsDto>`. Do not make all API responses nullable without a reason.

## 8. API Services

1. Use Axios for HTTP requests.
2. Get the configured Axios instance through the existing `useApiFetch` composable.
3. Group API methods into exported service objects.
4. Name services using the `<feature>Service` pattern.
5. Pass `$fetch: AxiosInstance` as the first argument to every service method.
6. Keep services responsible only for HTTP communication.
7. Type responses using `ApiResponse<T>` and the appropriate DTO.
8. Extract repeated API route prefixes into constants.
9. Do not introduce additional API wrappers without a clear need.

File: `src/app/services/dashboard/dashboard.service.ts`

```ts
import type { AxiosInstance } from 'axios'
import type { ApiResponse } from '@/app/types/api-response'
import type { DashboardStatisticsDto } from '@/app/types/dashboard/dashboard-statistics-dto'

const ROUTE_PREFIX_DASHBOARD = 'v1/dashboard'

export const dashboardService = {
  async fetchDashboard($fetch: AxiosInstance) {
    return await $fetch.get<ApiResponse<DashboardStatisticsDto>>(
      ROUTE_PREFIX_DASHBOARD,
    )
  },
}
```

The page or feature composable is responsible for calling the service, managing `isLoading`, handling errors, invoking the mapper, updating state, and displaying notifications.

```ts
const $fetch = useApiFetch()

const dashboard = ref<Nullable<DashboardStatisticInterface>>(null)
const isLoading = ref(false)
const error = ref(false)

async function onLoading() {
  if (isLoading.value) return

  isLoading.value = true
  error.value = false

  try {
    const { data } = await dashboardService.fetchDashboard($fetch)
    dashboard.value = DashboardMapper.toEntity(data.data)
  } catch (err: unknown) {
    console.error('Dashboard loading failed:', err)
    error.value = true
  } finally {
    isLoading.value = false
  }
}
```

## 9. Mappers and Data Validation

1. Use dedicated mapper classes to convert DTOs into client-side entities.
2. Name mapper classes using the `<Feature>Mapper` pattern.
3. Name mapper files using the `<feature>.mapper.ts` pattern.
4. Use static methods.
5. Use `toEntity()` to transform backend data into a client-side entity.
6. Use `toPayload()` to transform client-side data into a request payload when necessary.
7. Do not put transformations inside API services or Vue templates.
8. Mappers must not make HTTP requests or modify reactive state.
9. Keep transformations explicit and readable.
10. Use Zod validation where runtime validation is needed; do not add unnecessary schemas.

File: `src/app/mappers/dashboard.mapper.ts`

```ts
import type { DashboardStatisticsDto } from '@/app/types/dashboard/dashboard-statistics-dto'
import type { DashboardStatisticInterface } from '@/app/types/dashboard/dashboard-statistic-interface'

export class DashboardMapper {
  static toEntity(data: DashboardStatisticsDto): DashboardStatisticInterface {
    if (!data) {
      throw new Error('Dashboard data is required')
    }

    return {
      balance: data.total_balance,
      income: data.monthly_income,
      expenses: data.monthly_expenses,
      activeCredits: data.active_loans_count,
    }
  }
}
```

## 10. Lodash Usage

1. Use Lodash when it significantly simplifies data processing.
2. Prefer native JavaScript methods for simple operations.
3. Do not use Lodash instead of basic `map`, `filter`, `find`, `some`, or `reduce` without a reason.
4. Import only the functions needed, not the entire library.
5. Do not add Lodash as a dependency when native methods are sufficient.
6. Avoid unnecessary mutation of Vue reactive state.
7. Keep transformations readable and type-safe.

```ts
const activeItems = items.filter((item) => item.isActive)
```

## 11. Loading States and Skeleton Components

1. Use PrimeVue `Skeleton` for loading placeholders.
2. Prefer skeletons over a single spinner for cards, charts, tables, and lists.
3. **Extract skeleton markup into dedicated Vue components.**
4. Name skeleton components using `<ComponentName>Skeleton.vue`.
5. Place skeletons alongside their corresponding feature components.
6. Match the actual content's dimensions, spacing, and structure.
7. Use Tailwind CSS for layouts and styling.
8. Support mobile devices and both light and dark themes.
9. Do not duplicate complex skeleton markup across pages.
10. Do not create generic skeleton abstractions without practical benefit.
11. Use `aria-busy` on loading regions when appropriate.
12. Respect `prefers-reduced-motion`.
13. Do not block independent sections while another section is loading.

File: `src/app/features/dashboard/components/FinanceStatCardSkeleton.vue`

```vue
<script setup lang="ts">
import Skeleton from 'primevue/skeleton'
</script>

<template>
  <div class="rounded-3xl border border-fino-border bg-fino-surface p-5 sm:p-6">
    <div class="flex items-start justify-between gap-4">
      <Skeleton width="55%" height="0.875rem" />
      <Skeleton shape="circle" size="2.5rem" />
    </div>

    <Skeleton width="75%" height="2rem" class="mt-6" />
    <Skeleton width="60%" height="0.75rem" class="mt-4" />
  </div>
</template>
```

Usage:

```vue
<div
  v-if="isLoading"
  class="grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-4"
  aria-busy="true"
>
  <FinanceStatCardSkeleton v-for="index in 4" :key="index" />
</div>
```

## 12. Errors and Notifications

1. Use PrimeVue Toast for user-facing notifications.
2. Use the globally registered `ToastService`.
3. Access Toast with `useToast()` in components and composables.
4. Localize notification titles and messages with Vue I18n.
5. Use `severity: 'error'` for failures and `severity: 'success'` for completed user actions.
6. Do not show success notifications for routine page loads.
7. Use local error states for failures affecting individual sections.
8. Handle requests with `try/catch/finally`.
9. Use `unknown` for caught errors.

```ts
toast.add({
  severity: 'error',
  summary: t('toast.error'),
  detail: t('toast.dashboardLoadError'),
  life: 4000,
})
```

## 13. Async Data and UI State

1. Prevent duplicate concurrent requests for the same operation when unnecessary.
2. Keep independent page sections independent in their state management where possible.
3. Show skeletons only where data is actually loading.
4. Use stable keys in `v-for`.
5. Keep mocks in `src/app/mocks/`.
6. Never silently replace production API errors with mock data.
7. Do not overcomplicate state management without a clear reason.
8. Provide loading, error, and empty states where appropriate.

## 14. Animations and Transitions

1. Use Vue `Transition` and `TransitionGroup` for enter, leave, and list-movement animations.
2. Prefer Tailwind CSS transitions for hover, focus, and active states.
3. Keep animations subtle, fast, and consistent.
4. Do not add animation libraries without a clear need.
5. Extract repeated effects into shared styles when justified.
6. Respect `prefers-reduced-motion`.
7. Do not compromise readability or usability with animations.
8. Avoid layout shifts when switching from skeletons to content.
9. Use animation for meaningful feedback, not merely decoration.

## 15. Imports and Files

1. Use the existing `@/app/` alias.
2. Use `import type` for type-only imports.
3. Use kebab-case for interface, DTO, schema, and utility filenames.
4. Use PascalCase for Vue component filenames.
5. Give files clear feature-specific names.
6. Do not introduce alternative naming conventions without a reason.
7. Keep related files in existing directories.
8. Do not create new directories when a suitable location already exists.

```ts
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { dashboardService } from '@/app/services/dashboard/dashboard.service'
import { DashboardMapper } from '@/app/mappers/dashboard.mapper'
import type { DashboardStatisticInterface } from '@/app/types/dashboard/dashboard-statistic-interface'
import type { Nullable } from '@/app/types/nullable'
```

## 16. General Implementation Principles

1. Study the existing architecture before proposing changes.
2. Keep new code consistent with the existing codebase.
3. Separate API service, mapper, type, and UI responsibilities.
4. Extract components when they remove meaningful duplication; always keep skeleton layouts in dedicated components.
5. Do not extract trivial code without a clear benefit.
6. Account for loading, error, and empty states.
7. Preserve a consistent design across light and dark themes.
8. Do not break existing functionality when adding features.
9. Use existing dependencies when they already solve the problem.
10. Prefer complete, readable, maintainable solutions without unnecessary complexity.
