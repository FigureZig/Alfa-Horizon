import type { CreditScoreDto } from '@/app/types/company/credit-score-dto'
import type { CreditScoreInterface } from '@/app/types/company/credit-score-interface'

export class CreditScoreMapper {
  static toEntity(data: CreditScoreDto): CreditScoreInterface {
    if (!data) {
      throw new Error('Credit score data is required')
    }

    // Рычаги приходят без названий факторов — берём их из вкладов
    const titles = new Map(data.contributions.map((item) => [item.factor, item.title]))

    return {
      score: data.score,
      riskClass: data.class,
      bestClass: data.best_class,
      bkiKnown: data.bki_known,
      hasMissingFactors: data.missing.length > 0,
      factors: data.contributions.map((item) => ({
        factor: item.factor,
        title: item.title,
        value: item.value,
        points: item.points,
        effect: item.effect,
        text: item.text,
      })),
      levers: data.levers.map((lever) => ({
        factor: lever.factor,
        title: titles.get(lever.factor) ?? lever.factor,
        value: lever.value,
        target: lever.target,
        way: lever.way,
        gain: lever.gain,
      })),
      classes: data.classes.map((item) => ({ riskClass: item.class, min: item.min })),
    }
  }
}
