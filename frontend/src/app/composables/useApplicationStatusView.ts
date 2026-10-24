import { computed, toValue } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import type { RouteLocationRaw } from 'vue-router'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'
import { ApplicationStatusToneEnum } from '@/app/types/application/application-status-tone-enum'
import { ApprovalStatusEnum } from '@/app/types/application/approval-status-enum'
import { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import { DecisionKindEnum } from '@/app/types/application/decision-kind-enum'
import { DecisionOfferKindEnum } from '@/app/types/application/decision-offer-kind-enum'
import { SigningModeEnum } from '@/app/types/application/signing-mode-enum'
import type { ApplicationExplanationInterface } from '@/app/types/application/application-explanation-interface'
import type { ApplicationInterface } from '@/app/types/application/application-interface'
import type {
  ApplicationStatusActionInterface,
  ApplicationStatusViewInterface,
} from '@/app/types/application/application-status-view-interface'
import type { CompanyDirectorInterface } from '@/app/types/company/company-profile-interface'
import type { Nullable } from '@/app/types/nullable'

interface StatusSourceInterface {
  application: ApplicationInterface
  // Объяснение решения: из него первая строка «что сделать — что дадут»
  explanation: Nullable<ApplicationExplanationInterface>
  // ИНН того, кто смотрит, из GET /me
  personInn: Nullable<string>
  directors: CompanyDirectorInterface[]
  // Сегодня по часам мира, YYYY-MM-DD
  today: Nullable<string>
}

type ViewDraft = Omit<ApplicationStatusViewInterface, 'deadline' | 'isDeadlineUrgent' | 'primary' | 'secondary' | 'hint'>
  & Partial<Pick<ApplicationStatusViewInterface, 'primary' | 'secondary' | 'hint'>>

const URGENT_DAYS = 1

// Шаги степпера: подача, проверка, решение, подпись, выдача; у закрытых заявок степпера нет
const STATUS_STEPS: Partial<Record<ApplicationDetailStatusEnum, number>> = {
  [ApplicationDetailStatusEnum.Draft]: -1,
  [ApplicationDetailStatusEnum.Submitted]: 0,
  [ApplicationDetailStatusEnum.Checking]: 1,
  [ApplicationDetailStatusEnum.InfoRequested]: 2,
  [ApplicationDetailStatusEnum.UnderReview]: 2,
  // Банк уже решил: дальше клиент принимает оферту и подписывает — активен шаг подписи, а не «Решение»
  [ApplicationDetailStatusEnum.Offered]: 3,
  [ApplicationDetailStatusEnum.Signing]: 3,
  [ApplicationDetailStatusEnum.Signed]: 4,
  [ApplicationDetailStatusEnum.Disbursing]: 4,
  [ApplicationDetailStatusEnum.Issued]: 5,
}
const ISSUE_STEP = 4

const SPINNER = 'pi pi-spinner pi-spin'

/**
 * Шапка заявки для того, кто смотрит (таблица состояний из разбора UX): заголовок говорит, что сейчас происходит
 * для меня, подзаголовок — что дальше и кто действует, кнопка — только из `available_actions` или переход.
 * Права не вычисляем: что я могу сделать, решил бэкенд; имена берём из заявки и профиля компании.
 */
export function useApplicationStatusView(source: MaybeRefOrGetter<Nullable<StatusSourceInterface>>) {
  const { t } = useI18n({ useScope: 'global' })
  const { formatMoney, formatTerm, formatPercent, formatDateTime, formatList, formatShortName, getDaysLeft } = useFormatters()

  function formatDay(iso: string): string {
    return formatDateTime(iso, { day: 'numeric', month: 'long' })
  }

  function formatMoment(iso: string): string {
    return formatDateTime(iso, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })
  }

  // Имена по ИНН: руководители из профиля, подписи, участники, автор заявки
  function getNames(src: StatusSourceInterface, inns: string[]): string {
    const { application, directors } = src
    const names = inns
      .map((inn) =>
        directors.find((director) => director.inn === inn)?.fullName
        ?? application.signatures.find((signature) => signature.inn === inn)?.fio
        ?? application.approval?.participants.find((participant) => participant.inn === inn)?.fio
        ?? (application.createdBy?.inn === inn ? application.createdBy.name : null))
      .filter((name): name is string => Boolean(name))
      .map(formatShortName)

    return names.length ? formatList(names) : t('application.view.director')
  }

  function getDirectorNames(src: StatusSourceInterface): string {
    return getNames(src, src.directors.map((director) => director.inn))
  }

  // Первый путь к одобрению — директивно: «Банк даст все 10 млн ₽ под 21,7 %, если перевести обороты в банк»
  function getDirective(src: StatusSourceInterface): string {
    const { application, explanation } = src
    const option = explanation && !explanation.pathBlocked ? explanation.pathOptions[0] : null

    if (!option?.amount) return ''

    const amount = option.rate !== null
      ? t('application.view.directive.amountWithRate', { amount: formatMoney(option.amount), rate: formatPercent(option.rate) })
      : formatMoney(option.amount)

    if (application.status === ApplicationDetailStatusEnum.Rejected) {
      return t('application.view.directive.approve', { amount, action: option.title })
    }

    return option.amount >= application.request.amount
      ? t('application.view.directive.full', { amount, action: option.title })
      : t('application.view.directive.more', { amount, action: option.title })
  }

  // Новая заявка с теми же условиями: «Проверить снова», «Получить новое»
  function getRestartRoute(src: StatusSourceInterface, isAmountKept = true): RouteLocationRaw {
    const { request, companyInn } = src.application

    return {
      name: 'application-new',
      params: { inn: companyInn },
      query: {
        product: request.product,
        ...(isAmountKept ? { amount: request.amount } : {}),
        ...(request.termMonths ? { term: request.termMonths } : {}),
        ...(request.goal ? { goal: request.goal } : {}),
      },
    }
  }

  function getLink(label: string, to: RouteLocationRaw): ApplicationStatusActionInterface {
    return { label, command: null, to }
  }

  function getCommand(label: string, command: ApplicationActionEnum): ApplicationStatusActionInterface {
    return { label, command, to: null }
  }

  function viewOffered(src: StatusSourceInterface): ViewDraft {
    const { application } = src
    const offer = application.offers[0] ?? application.offer
    const amount = offer ? formatMoney(offer.amount) : ''
    const until = application.deadline ? formatDay(application.deadline.at) : ''
    const base = { tone: ApplicationStatusToneEnum.Action, icon: 'pi pi-wallet', substep: '' }

    if (!application.availableActions.includes(ApplicationActionEnum.AcceptOffer)) {
      return {
        ...base,
        tone: ApplicationStatusToneEnum.Neutral,
        title: t('application.view.offer.readOnly.title', { amount }),
        subtitle: t('application.view.offer.readOnly.subtitle', { names: getDirectorNames(src) }),
      }
    }

    if (application.flags.includes(ApplicationFlagEnum.Recheck)) {
      return {
        ...base,
        icon: 'pi pi-refresh',
        title: t('application.view.offer.recheck.title'),
        subtitle: t('application.view.offer.recheck.subtitle', { date: until }),
      }
    }

    if (application.flags.includes(ApplicationFlagEnum.Provisional)) {
      return {
        ...base,
        title: t('application.view.offer.provisional.title', { amount }),
        subtitle: t('application.view.offer.provisional.subtitle'),
      }
    }

    const offerKind = application.decision?.offerKind

    if (offerKind === DecisionOfferKindEnum.Counter || (offer && offer.amount < application.request.amount)) {
      return {
        ...base,
        title: t('application.view.offer.counter.title', { amount, requested: formatMoney(application.request.amount) }),
        subtitle: t('application.view.offer.counter.subtitle', { date: until }),
        hint: getDirective(src),
      }
    }

    if (offerKind === DecisionOfferKindEnum.Conditional) {
      const conditions = (application.decision?.conditions ?? []).map((condition) =>
        t(`application.offers.condition.${condition}`))

      return {
        ...base,
        title: t('application.view.offer.conditional.title', { amount }),
        subtitle: [formatList(conditions), t('application.view.offer.until', { date: until })].filter(Boolean).join(' · '),
      }
    }

    return {
      ...base,
      title: t('application.view.offer.asRequested.title', { amount, term: offer ? formatTerm(offer.termMonths) : '' }),
      subtitle: t('application.view.offer.until', { date: until }),
    }
  }

  function viewInfoRequested(src: StatusSourceInterface): ViewDraft {
    const { application } = src
    const until = application.deadline ? formatDay(application.deadline.at) : ''
    const approval = application.approval

    // Голосование участников за крупную сделку — тот же статус, другое ожидание
    if (approval) {
      if (application.availableActions.includes(ApplicationActionEnum.Vote)) {
        return {
          tone: ApplicationStatusToneEnum.Action,
          icon: 'pi pi-users',
          title: t('application.view.voting.mine.title', { date: until }),
          subtitle: t('application.view.voting.mine.subtitle'),
          substep: t('application.view.substep.voting'),
        }
      }

      const votedInns = approval.votes.map((vote) => vote.inn)
      const notVoted = approval.participants.filter((participant) => !votedInns.includes(participant.inn))
      const progress = t('application.view.voting.waiting.progress', {
        percent: formatPercent(approval.forPercent),
        threshold: formatPercent(approval.thresholdPercent),
      })

      return {
        tone: ApplicationStatusToneEnum.Neutral,
        icon: 'pi pi-users',
        title: t('application.view.voting.waiting.title'),
        subtitle: notVoted.length
          ? t('application.view.voting.waiting.subtitle', {
            progress,
            names: formatList(notVoted.map((participant) => formatShortName(participant.fio))),
          })
          : progress,
        substep: t('application.view.substep.voting'),
      }
    }

    const asks = application.infoRequest?.asks ?? []
    const what = asks.length
      ? formatList(asks.map((ask) => t(`application.view.asks.${ask}`)))
      : t('application.view.asks.default')

    if (application.availableActions.includes(ApplicationActionEnum.AnswerInfo)) {
      return {
        tone: ApplicationStatusToneEnum.Action,
        icon: 'pi pi-comment',
        title: until
          ? t('application.view.info.title', { what, date: until })
          : t('application.view.info.titleNoDate', { what }),
        subtitle: t('application.view.info.subtitle'),
        substep: t('application.view.substep.info'),
      }
    }

    return {
      tone: ApplicationStatusToneEnum.Neutral,
      icon: 'pi pi-comment',
      title: t('application.view.info.readOnly.title', { what }),
      subtitle: t('application.view.info.readOnly.subtitle', { names: getDirectorNames(src) }),
      substep: t('application.view.substep.info'),
    }
  }

  function viewUnderReview(src: StatusSourceInterface): ViewDraft {
    const { application } = src
    const time = application.slaUntil ? formatMoment(application.slaUntil) : ''
    const base = { tone: ApplicationStatusToneEnum.Neutral, icon: 'pi pi-user' }

    if (application.flags.includes(ApplicationFlagEnum.DisburseError)) {
      return {
        ...base,
        icon: 'pi pi-exclamation-circle',
        title: t('application.view.disburseError.title'),
        subtitle: time
          ? t('application.view.disburseError.subtitle', { time })
          : t('application.view.disburseError.subtitleNoTime'),
        substep: '',
      }
    }

    const isSlaBreached = application.flags.includes(ApplicationFlagEnum.SlaBreach)
    const subtitle = isSlaBreached || !time
      ? t('application.view.review.late')
      : t('application.view.review.subtitle', { time })

    if (application.pendingDecision) {
      return {
        ...base,
        icon: 'pi pi-key',
        title: t('application.view.secondKey.title'),
        subtitle: isSlaBreached || !time
          ? t('application.view.secondKey.late')
          : t('application.view.secondKey.subtitle', { time }),
        substep: t('application.view.substep.secondKey'),
      }
    }

    return { ...base, title: t('application.view.review.title'), subtitle, substep: t('application.view.substep.review') }
  }

  function viewSigning(src: StatusSourceInterface): ViewDraft {
    const { application, personInn } = src
    const until = application.deadline ? formatDay(application.deadline.at) : ''
    const signers = application.signers
    const signedInns = application.signatures.map((signature) => signature.inn)
    const isJoint = signers?.mode === SigningModeEnum.Joint
    const pendingInns = isJoint ? (signers?.required ?? []).filter((inn) => !signedInns.includes(inn)) : []

    if (application.flags.includes(ApplicationFlagEnum.Provisional)) {
      return {
        tone: ApplicationStatusToneEnum.Neutral,
        icon: 'pi pi-clock',
        title: t('application.view.signing.provisional.title'),
        subtitle: t('application.view.signing.provisional.subtitle'),
        substep: '',
      }
    }

    if (application.availableActions.includes(ApplicationActionEnum.Sign)) {
      const offer = application.offer ?? application.offers[0]
      const isLimit = offer?.product === CreditProductCodeEnum.Overdraft
      const terms = offer
        ? t(isLimit ? 'application.view.signing.mine.limitTerms' : 'application.view.signing.mine.loanTerms', {
          amount: formatMoney(offer.amount),
          rate: formatPercent(offer.rate),
          payment: formatMoney(offer.payment),
        })
        : ''

      return {
        tone: ApplicationStatusToneEnum.Action,
        icon: 'pi pi-pen-to-square',
        title: until ? t('application.view.signing.mine.title', { date: until }) : t('application.view.signing.mine.titleNoDate'),
        subtitle: terms,
        substep: '',
        primary: getCommand(t('application.view.signing.mine.action'), ApplicationActionEnum.Sign),
      }
    }

    // Совместная подпись: я уже подписал, ждём остальных
    if (isJoint && personInn && signedInns.includes(personInn) && pendingInns.length) {
      return {
        tone: ApplicationStatusToneEnum.Neutral,
        icon: 'pi pi-hourglass',
        title: t('application.view.signing.signed.title', { names: getNames(src, pendingInns) }),
        subtitle: t('application.view.signing.signed.subtitle', { date: until }),
        substep: '',
      }
    }

    const signerInns = isJoint ? pendingInns : (signers?.anyOf ?? [])
    const titleKey = isJoint && pendingInns.length > 1
      ? 'application.view.signing.others.titleAll'
      : signerInns.length > 1 ? 'application.view.signing.others.titleAny' : 'application.view.signing.others.title'
    const isMine = Boolean(personInn && application.createdBy?.inn === personInn)

    return {
      tone: ApplicationStatusToneEnum.Neutral,
      icon: 'pi pi-pen-to-square',
      title: t(titleKey, { names: getNames(src, signerInns) }),
      subtitle: isMine ? t('application.view.signing.others.prepared') : t('application.view.signing.others.noRight'),
      substep: '',
    }
  }

  function viewClosed(src: StatusSourceInterface): ViewDraft {
    const { application } = src
    const status = application.status
    const reason = application.decision?.reasons[0]?.text ?? ''
    const creditsRoute = { name: 'credits', params: { inn: application.companyInn } }

    if (status === ApplicationDetailStatusEnum.Rejected) {
      const isFixable = application.decision?.kind === DecisionKindEnum.StopFixable
        || Boolean(src.explanation && !src.explanation.pathBlocked && src.explanation.pathOptions.length)

      if (isFixable) {
        return {
          tone: ApplicationStatusToneEnum.Danger,
          icon: 'pi pi-times-circle',
          title: t('application.view.rejected.fixable.title'),
          subtitle: reason,
          hint: getDirective(src),
          substep: '',
          primary: getLink(t('application.view.rejected.fixable.action'), getRestartRoute(src)),
          secondary: getLink(t('application.view.actions.findCredit'), creditsRoute),
        }
      }

      return {
        tone: ApplicationStatusToneEnum.Danger,
        icon: 'pi pi-times-circle',
        title: t('application.view.rejected.final.title'),
        subtitle: application.decision?.kind === DecisionKindEnum.StopFinal && reason
          ? t('application.view.rejected.final.subtitle', { reason })
          : reason,
        substep: '',
        primary: getLink(t('application.view.actions.findCredit'), creditsRoute),
      }
    }

    if (status === ApplicationDetailStatusEnum.Withdrawn && application.approval?.status === ApprovalStatusEnum.Rejected) {
      return {
        tone: ApplicationStatusToneEnum.Danger,
        icon: 'pi pi-users',
        title: t('application.view.withdrawn.voting.title'),
        subtitle: t('application.view.withdrawn.voting.subtitle', { percent: formatPercent(application.approval.againstPercent) }),
        substep: '',
        primary: getLink(t('application.view.withdrawn.voting.action'), getRestartRoute(src, false)),
      }
    }

    if (status === ApplicationDetailStatusEnum.Expired) {
      // Какой шаг истёк: срок заявки помнит свой статус
      const expiredStep = application.deadline?.status
      const date = application.deadline ? formatDay(application.deadline.at) : ''
      const isOffer = expiredStep === ApplicationDetailStatusEnum.Offered
      const stepKey = expiredStep === ApplicationDetailStatusEnum.Signing
        ? 'signing'
        : expiredStep === ApplicationDetailStatusEnum.InfoRequested
          ? (application.approval ? 'voting' : 'info')
          : 'draft'

      return {
        tone: ApplicationStatusToneEnum.Neutral,
        icon: 'pi pi-clock',
        title: isOffer ? t('application.view.expired.offer.title', { date }) : t(`application.view.expired.${stepKey}`, { date }),
        subtitle: isOffer ? t('application.view.expired.offer.subtitle') : t('application.view.closed'),
        substep: '',
        primary: getLink(
          isOffer ? t('application.view.expired.offer.action') : t('application.view.actions.again'),
          getRestartRoute(src),
        ),
      }
    }

    const isDeclined = status === ApplicationDetailStatusEnum.Declined

    return {
      tone: ApplicationStatusToneEnum.Neutral,
      icon: isDeclined ? 'pi pi-ban' : 'pi pi-undo',
      title: isDeclined ? t('application.view.declined') : t('application.view.withdrawn.self'),
      subtitle: t('application.view.closed'),
      substep: '',
      primary: getLink(t('application.view.actions.newApplication'), getRestartRoute(src)),
    }
  }

  function viewIssued(src: StatusSourceInterface): ViewDraft {
    const { application } = src
    const loan = application.loan
    const offer = application.offer ?? application.offers[0]
    const amount = formatMoney(loan?.amount ?? offer?.amount ?? application.request.amount)
    const homeRoute = { name: 'dashboard', params: { inn: application.companyInn } }
    const base = {
      tone: ApplicationStatusToneEnum.Success,
      icon: 'pi pi-check-circle',
      substep: '',
      primary: getLink(t('application.view.actions.home'), homeRoute),
    }

    if (loan?.isLimit) {
      return {
        ...base,
        title: t('application.view.issued.limit.title', { amount }),
        subtitle: loan.number
          ? t('application.view.issued.limit.subtitle', { number: loan.number, amount })
          : t('application.view.issued.limit.subtitleNoNumber', { amount }),
      }
    }

    const payment = offer ? formatMoney(offer.payment) : ''

    return {
      ...base,
      title: t('application.view.issued.loan.title', { amount }),
      subtitle: loan?.number && payment
        ? t('application.view.issued.loan.subtitle', { number: loan.number, payment })
        : payment ? t('application.view.issued.loan.subtitleNoNumber', { payment }) : '',
    }
  }

  function buildDraft(src: StatusSourceInterface): ViewDraft {
    const { application } = src

    switch (application.status) {
      case ApplicationDetailStatusEnum.Draft:
        return {
          tone: ApplicationStatusToneEnum.Neutral,
          icon: 'pi pi-file-edit',
          title: t('application.view.draft.title'),
          subtitle: t('application.view.draft.subtitle'),
          substep: '',
          primary: application.availableActions.includes(ApplicationActionEnum.Submit)
            ? getCommand(t('application.view.draft.action'), ApplicationActionEnum.Submit)
            : null,
        }
      case ApplicationDetailStatusEnum.Submitted:
      case ApplicationDetailStatusEnum.Checking: {
        const isRecheck = application.flags.includes(ApplicationFlagEnum.Recheck)

        return {
          tone: ApplicationStatusToneEnum.Busy,
          icon: SPINNER,
          title: isRecheck ? t('application.view.recheck.title') : t('application.view.checking.title'),
          subtitle: t('application.view.checking.subtitle'),
          substep: '',
        }
      }
      case ApplicationDetailStatusEnum.InfoRequested:
        return viewInfoRequested(src)
      case ApplicationDetailStatusEnum.UnderReview:
        return viewUnderReview(src)
      case ApplicationDetailStatusEnum.Offered:
        return viewOffered(src)
      case ApplicationDetailStatusEnum.Signing:
        return viewSigning(src)
      case ApplicationDetailStatusEnum.Signed:
      case ApplicationDetailStatusEnum.Disbursing: {
        const offer = application.offer ?? application.offers[0]

        return {
          tone: ApplicationStatusToneEnum.Busy,
          icon: SPINNER,
          title: offer?.product === CreditProductCodeEnum.Overdraft
            ? t('application.view.signed.limit')
            : t('application.view.signed.loan'),
          subtitle: t('application.view.signed.subtitle'),
          substep: '',
        }
      }
      case ApplicationDetailStatusEnum.Issued:
        return viewIssued(src)
      default:
        return viewClosed(src)
    }
  }

  // Сколько осталось на текущем шаге: дни по часам мира; у закрытых заявок срока нет
  function getDeadline(src: StatusSourceInterface): { text: string; isUrgent: boolean } {
    const { application, today } = src
    // У черновика срок — когда он закроется сам; к действию он не подгоняет, поэтому не показываем
    const isDraft = application.status === ApplicationDetailStatusEnum.Draft
    const at = !isDraft && application.deadline?.status === application.status ? application.deadline.at : null

    if (!at || !today) return { text: '', isUrgent: false }

    const daysLeft = getDaysLeft(at, today)

    return {
      text: daysLeft === 0 ? t('application.view.deadline.today') : t('application.view.deadline.days', daysLeft),
      isUrgent: daysLeft <= URGENT_DAYS,
    }
  }

  const view = computed<Nullable<ApplicationStatusViewInterface>>(() => {
    const src = toValue(source)

    if (!src) return null

    const draft = buildDraft(src)
    const deadline = getDeadline(src)

    return {
      ...draft,
      hint: draft.hint ?? '',
      primary: draft.primary ?? null,
      secondary: draft.secondary ?? null,
      deadline: deadline.text,
      isDeadlineUrgent: deadline.isUrgent,
    }
  })

  // Шаг степпера: выдача с ошибкой АБС — всё ещё шаг выдачи, хоть заявка и у специалиста
  const step = computed<Nullable<number>>(() => {
    const application = toValue(source)?.application

    if (!application) return null

    if (application.flags.includes(ApplicationFlagEnum.DisburseError)) return ISSUE_STEP

    return STATUS_STEPS[application.status] ?? null
  })

  return { view, step }
}
