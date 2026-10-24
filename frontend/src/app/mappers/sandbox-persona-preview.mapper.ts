import type {
  SandboxPersonaPreviewCauseDto,
  SandboxPersonaPreviewDto,
  SandboxPersonaPreviewProductDto,
} from '@/app/types/sandbox/sandbox-persona-preview-dto'
import type {
  SandboxPersonaPreviewCauseInterface,
  SandboxPersonaPreviewInterface,
  SandboxPersonaPreviewProductInterface,
} from '@/app/types/sandbox/sandbox-persona-preview-interface'

const LABEL_RANKS: Record<string, number> = {
  PREAPPROVED: 0,
  CONDITIONAL: 1,
  REVIEW: 2,
  UNAVAILABLE: 3,
}

export class SandboxPersonaPreviewMapper {
  static toEntity(data: SandboxPersonaPreviewDto): SandboxPersonaPreviewInterface {
    if (!data) {
      throw new Error('Sandbox persona preview data is required')
    }

    return {
      companyName: data.company.name,
      about: data.company.about,
      pathMeans: data.path.means,
      signMode: data.path.sign_mode ?? null,
      people: data.people.map((person) => ({
        badge: person.badge,
        fullName: person.full_name,
        roleTitle: person.role_title,
      })),
      score: data.score.score,
      riskClass: data.score.class,
      scoreFields: data.score.factors
        .filter((factor) => factor.effect === 'minus')
        .flatMap((factor) => factor.fields),
      blockers: data.blockers.map((cause) => SandboxPersonaPreviewMapper.toCause(cause)),
      products: data.products
        .map((product) => SandboxPersonaPreviewMapper.toProduct(product))
        .sort((first, second) => first.rank - second.rank || Number(second.isRecommended) - Number(first.isRecommended)),
    }
  }

  private static toCause(cause: SandboxPersonaPreviewCauseDto): SandboxPersonaPreviewCauseInterface {
    return { code: cause.code, text: cause.text, fields: cause.fields }
  }

  private static toProduct(product: SandboxPersonaPreviewProductDto): SandboxPersonaPreviewProductInterface {
    return {
      code: product.product,
      name: product.name,
      isAvailable: product.available,
      rank: LABEL_RANKS[product.label] ?? LABEL_RANKS.UNAVAILABLE,
      label: product.label,
      maxAmount: product.max_amount,
      rate: product.rate,
      causes: product.why.map((cause) => SandboxPersonaPreviewMapper.toCause(cause)),
      isRecommended: product.recommended,
    }
  }
}
