import type { ApplicationExplanationDto } from '@/app/types/application/application-explanation-dto'
import type { ApplicationExplanationInterface } from '@/app/types/application/application-explanation-interface'

export class ApplicationExplanationMapper {
  static toEntity(data: ApplicationExplanationDto): ApplicationExplanationInterface {
    if (!data) {
      throw new Error('Application explanation data is required')
    }

    return {
      outcome: data.outcome,
      reasons: data.reasons.map((reason) => ({ code: reason.code, kind: reason.kind, text: reason.text })),
      score: data.scoring.score,
      riskClass: data.scoring.risk_class,
      factors: data.scoring.factors.map((factor) => ({
        factor: factor.factor,
        title: factor.title,
        points: factor.points,
        effect: factor.effect,
        text: factor.text,
        gain: factor.next?.gain ?? null,
      })),
      rate: data.price ? Number(data.price.total) : null,
      priceParts: (data.price?.parts ?? []).map((part) => ({
        part: part.part,
        value: Number(part.value),
        text: part.text,
      })),
      caps: (data.limit?.caps ?? []).map((cap) => ({
        code: cap.code,
        text: cap.text,
        isBinding: cap.binding ?? cap.code === data.limit?.binding,
      })),
      pathTitle: data.path_to_approval.title ?? null,
      pathBlocked: !data.path_to_approval.changeable,
      pathOptions: data.path_to_approval.options.map((option) => ({
        title: option.title,
        outcome: option.outcome,
        riskClass: option.risk_class,
        amount: option.amount === null ? null : Number(option.amount),
        rate: option.rate === null ? null : Number(option.rate),
      })),
    }
  }
}
