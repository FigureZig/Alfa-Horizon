import type { Nullable } from '@/app/types/nullable'

export interface CompanyAccessInterface {
  inn: string
  name: string
  shortName: string
  canView: boolean
  canApprove: boolean
  // Доля участника ООО, %
  share: Nullable<number>
}

export interface MeInterface {
  personInn: Nullable<string>
  companies: CompanyAccessInterface[]
}
