// Флаг включён, пока явно не задан как false: так локальный .env без флагов не прячет функции
function isFeatureEnabled(value: string | undefined): boolean {
  return value !== 'false'
}

export function useFeatureFlags() {
  return {
    isK1Enabled: isFeatureEnabled(import.meta.env.FEATURE_K1),
    isK2Enabled: isFeatureEnabled(import.meta.env.FEATURE_K2),
  }
}
