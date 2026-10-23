import { BankNoteMapper } from '@/app/mappers/bank-note.mapper'
import { ApplicationProductChoiceEnum } from '@/app/types/application/application-product-choice-enum'
import type {
  ApplicationDecisionDto,
  ApplicationDto,
  ApplicationOfferDto,
} from '@/app/types/application/application-dto'
import type {
  ApplicationDecisionInterface,
  ApplicationInterface,
  ApplicationOfferInterface,
} from '@/app/types/application/application-interface'
import type { ApplicationCreateDto, ApplicationInfoAnswerDto } from '@/app/types/application/application-create-dto'
import type {
  ApplicationFormInterface,
  ApplicationInfoAnswerInterface,
} from '@/app/types/application/application-form-interface'

export class ApplicationMapper {
  static toEntity(data: ApplicationDto): ApplicationInterface {
    if (!data) {
      throw new Error('Application data is required')
    }

    return {
      id: data.id,
      companyInn: data.company_inn,
      status: data.status,
      flags: data.flags,
      createdAt: data.created_at,
      updatedAt: data.updated_at,
      request: {
        product: data.request.product,
        amount: Number(data.request.amount),
        termMonths: data.request.term_months ?? null,
        goal: data.request.goal ?? null,
      },
      consentBki: data.consent_bki,
      decision: data.decision ? ApplicationMapper.toDecision(data.decision) : null,
      offer: data.offer ? ApplicationMapper.toOffer(data.offer) : null,
      offers: data.offers.map((offer) => ApplicationMapper.toOffer(offer)),
      infoRequest: data.info_request
        ? { asks: data.info_request.asks, comment: data.info_request.comment ?? null }
        : null,
      signers: data.signers
        ? { mode: data.signers.mode, anyOf: data.signers.any_of, required: data.signers.required }
        : null,
      signatures: data.signatures.map((signature) => ({
        inn: signature.inn,
        fio: signature.fio,
        role: signature.role,
        at: signature.at,
      })),
      approval: data.approval
        ? {
          status: data.approval.status,
          participants: data.approval.participants.map((participant) => ({
            inn: participant.inn,
            fio: participant.fio,
            share: participant.share,
          })),
          votes: data.approval.votes.map((vote) => ({ inn: vote.inn, fio: vote.fio ?? null, vote: vote.vote })),
          forPercent: data.approval.for_pct,
          againstPercent: data.approval.against_pct,
          thresholdPercent: data.approval.threshold_pct,
        }
        : null,
      loan: data.loan
        ? {
          isLimit: data.loan.kind === 'limit',
          number: data.loan.number ?? data.loan.loan_id,
          loanId: data.loan.loan_id,
          amount: Number(data.loan.amount),
          rate: Number(data.loan.rate),
          termMonths: data.loan.term_months,
          disbursedAt: data.loan.disbursed_at,
        }
        : null,
      deadline: data.deadline
        ? { status: data.deadline.status, at: data.deadline.at, then: data.deadline.then }
        : null,
      slaUntil: data.sla_until,
      pendingDecision: data.pending_decision ? BankNoteMapper.toEntity(data.pending_decision) : null,
      bankDecision: data.bank_decision ? BankNoteMapper.toEntity(data.bank_decision) : null,
      availableActions: data.available_actions,
    }
  }

  static toCreatePayload(inn: string, form: ApplicationFormInterface): ApplicationCreateDto {
    if (!form.product || form.amount === null) {
      throw new Error('Application product and amount are required')
    }

    return {
      inn,
      product: form.product === ApplicationProductChoiceEnum.BankChoice ? undefined : form.product,
      amount: form.amount,
      term_months: form.termMonths ?? undefined,
      goal: form.goal ?? undefined,
      consent_bki: form.consentBki,
    }
  }

  static toInfoAnswerPayload(answer: ApplicationInfoAnswerInterface): ApplicationInfoAnswerDto {
    return {
      corporate_approval: answer.corporateApproval || undefined,
      collateral_value: answer.collateralValue ?? undefined,
      documents: answer.documents.length ? answer.documents : undefined,
      comment: answer.comment.trim() || undefined,
    }
  }

  static toOffer(offer: ApplicationOfferDto): ApplicationOfferInterface {
    return {
      product: offer.product,
      productName: offer.product_name,
      amount: Number(offer.amount),
      termMonths: offer.term_months,
      payment: Number(offer.payment),
      repayment: offer.repayment,
      rate: Number(offer.rate.total),
      riskClass: offer.rate.risk_class,
      variant: offer.variant ?? null,
    }
  }

  private static toDecision(decision: ApplicationDecisionDto): ApplicationDecisionInterface {
    return {
      outcome: decision.outcome,
      offerKind: decision.offer_kind,
      counter: decision.counter,
      conditions: decision.conditions,
      asks: decision.asks,
      reasons: decision.reasons.map((reason) => ({ code: reason.code, kind: reason.kind, text: reason.text })),
      hints: decision.hints,
    }
  }
}
