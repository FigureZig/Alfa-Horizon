import { ApplicationMapper } from '@/app/mappers/application.mapper'
import { BankNoteMapper } from '@/app/mappers/bank-note.mapper'
import type { BankQueueItemDto } from '@/app/types/bank/bank-queue-item-dto'
import type { BankQueueItemInterface } from '@/app/types/bank/bank-queue-item-interface'

export class BankQueueMapper {
  static toEntity(data: BankQueueItemDto): BankQueueItemInterface {
    if (!data) {
      throw new Error('Bank queue item data is required')
    }

    return {
      id: data.id,
      inn: data.inn,
      status: data.status,
      flags: data.flags,
      request: {
        product: data.request.product,
        amount: Number(data.request.amount),
        termMonths: data.request.term_months ?? null,
        goal: data.request.goal ?? null,
      },
      reasons: data.reasons.map((reason) => ({ code: reason.code, kind: reason.kind, text: reason.text })),
      proposal: data.proposal ? ApplicationMapper.toOffer(data.proposal) : null,
      score: data.risk?.score ?? null,
      riskClass: data.risk?.class ?? null,
      pendingDecision: data.pending_decision ? BankNoteMapper.toEntity(data.pending_decision) : null,
      availableActions: data.available_actions,
      slaUntil: data.sla_until,
      updatedAt: data.updated_at,
    }
  }
}
