export enum SandboxEventTypeEnum {
  TaxDebtAppeared = 'fns.tax_debt_appeared',
  TaxDebtPaid = 'fns.tax_debt_paid',
  BankruptcyStarted = 'legal.bankruptcy_started',
  UnreliableFlag = 'egrul.unreliable_flag',
  LiquidationStarted = 'egrul.liquidation_started',
  DirectorChanged = 'egrul.director_changed',
  PowerOfAttorneyRevoked = 'mchd.revoked',
  ContractSigned = 'eis.contract_signed',
}
