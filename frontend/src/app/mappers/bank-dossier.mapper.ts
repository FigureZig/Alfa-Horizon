import type { BankDossierDto } from '@/app/types/bank/bank-dossier-dto'
import type { BankDossierInterface } from '@/app/types/bank/bank-dossier-interface'

export class BankDossierMapper {
  static toEntity(data: BankDossierDto): BankDossierInterface {
    if (!data) {
      throw new Error('Bank dossier data is required')
    }

    const facts = data.facts

    return {
      facts: {
        name: facts.name,
        inn: facts.inn,
        segment: facts.segment,
        okved: facts.okved,
        okvedName: facts.okved_name,
        registeredAt: facts.registered,
        ageMonths: facts.age_months,
        headcount: facts.headcount,
        taxRegime: facts.tax_regime,
        taxDebt: facts.tax_debt === null ? null : Number(facts.tax_debt),
        monthlyInflow: facts.inflow_avg === null ? null : Number(facts.inflow_avg),
        inflowVariation: facts.inflow_cv,
        debtLoad: facts.debt_load,
        maxOverdueDays: facts.max_overdue_days,
        bkiRequests: facts.bki_requests_30d,
        isBkiKnown: facts.bki_known,
      },
      sources: data.sources.map((source) => ({
        source: source.source,
        status: source.status,
        fetchedAt: source.fetched_at,
        isStale: source.stale,
      })),
    }
  }
}
