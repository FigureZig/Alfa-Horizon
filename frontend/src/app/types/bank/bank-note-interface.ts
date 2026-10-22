import type { ApplicationOfferInterface } from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

export interface BankSecondKeyInterface {
  by: string
  at: string
  isApproved: boolean
  comment: Nullable<string>
}

export interface BankNoteInterface {
  at: string
  by: string
  action: string
  comment: Nullable<string>
  limit: Nullable<number>
  offer: Nullable<ApplicationOfferInterface>
  secondKey: Nullable<BankSecondKeyInterface>
}
