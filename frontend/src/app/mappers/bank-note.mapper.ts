import { ApplicationMapper } from '@/app/mappers/application.mapper'
import type { BankNoteDto } from '@/app/types/bank/bank-note-dto'
import type { BankNoteInterface } from '@/app/types/bank/bank-note-interface'

export class BankNoteMapper {
  static toEntity(data: BankNoteDto): BankNoteInterface {
    if (!data) {
      throw new Error('Bank note data is required')
    }

    return {
      at: data.at,
      by: data.by,
      action: data.action,
      comment: data.comment ?? null,
      limit: data.limit ?? null,
      offer: data.offer ? ApplicationMapper.toOffer(data.offer) : null,
      secondKey: data.second_key
        ? {
          by: data.second_key.by,
          at: data.second_key.at,
          isApproved: data.second_key.action === 'confirm',
          comment: data.second_key.comment,
        }
        : null,
    }
  }
}
