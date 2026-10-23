// Что мешает банку предложить кредит всей компании: недоимка, банкротство, недостоверный директор, лимит нагрузки…
export interface CompanyBlockerDto {
  code: string
  text: string
}

/** Ответ GET v1/companies/{inn}/offers без цели: подбор по всем продуктам, здесь нужны только стоп-факторы. */
export interface CompanyOffersDto {
  inn: string
  blockers: CompanyBlockerDto[]
}
