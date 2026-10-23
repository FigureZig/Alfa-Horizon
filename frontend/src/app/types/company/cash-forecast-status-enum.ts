export enum CashForecastStatusEnum {
  CashGap = 'CASH_GAP',
  // Минус есть, но его покрывает подключённый овердрафт
  Covered = 'COVERED',
  Healthy = 'HEALTHY',
}
