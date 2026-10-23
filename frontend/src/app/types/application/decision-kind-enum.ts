// Вид отказа: стоп-фактор, который компания может устранить, окончательный стоп или правило продукта
export enum DecisionKindEnum {
  StopFixable = 'STOP_FIXABLE',
  StopFinal = 'STOP_FINAL',
  Policy = 'POLICY',
}
