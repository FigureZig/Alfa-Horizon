"""Схемы ответов API для OpenAPI (Swagger /api/docs, ReDoc /api/redoc).

Ручки отдают словари через http.ok(); модели здесь описывают их форму в документации (`responses={200: {"model": …}}`)
и не фильтруют ответ на лету. Что ответы совпадают с описанием, проверяют сквозные тесты: каждый ответ в tests/e2e
проходит валидацию моделью своей ручки (tests/e2e/conftest.py).
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Money = str            # деньги в ядре API — строкой: Decimal без потерь, "400000.00"
Status = Literal["DRAFT", "SUBMITTED", "CHECKING", "INFO_REQUESTED", "UNDER_REVIEW", "OFFERED", "SIGNING", "SIGNED",
                 "DISBURSING", "ISSUED", "REJECTED", "DECLINED", "WITHDRAWN", "EXPIRED"]
Outcome = Literal["APPROVE", "COUNTER_OFFER", "APPROVE_WITH_CONDITIONS", "REQUEST_INFO", "MANUAL_REVIEW", "REJECT"]
Product = Literal["OVERDRAFT", "EXPRESS", "WORKING_CAPITAL", "INVESTMENT", "CONTRACT", "AGRO_SEASONAL"]
Action = Literal["submit", "withdraw", "accept_offer", "decline_offer", "answer_info", "sign", "vote", "decide", "confirm"]
FrontStatus = Literal["DRAFT", "SUBMITTED", "IN_REVIEW", "ACTION_REQUIRED", "APPROVED", "REJECTED", "ISSUED"]


class Schema(BaseModel):
    model_config = ConfigDict(extra="allow")


class Envelope[T](BaseModel):
    """Успешный ответ: полезные данные в `data`, служебное — в `meta`."""
    data: T
    meta: dict[str, Any] | None = Field(None, description="служебные сведения, например дата мира симулятора")


# ── ошибки ───────────────────────────────────────────────────────────────────────────────────────────────────────


class ValidationIssue(Schema):
    loc: list[str | int] = Field(description="где ошибка: ['body', 'amount']")
    msg: str
    type: str


class ProblemDetails(Schema):
    """Ошибка по RFC 9457 (`application/problem+json`). Ветвиться — по `code`, `detail` — текст для людей.
    Дополнительные поля зависят от кода: `errors` у 422, `right`/`roles`/`why` у 403, `app_status` у 409 и т. п."""
    type: str = Field("about:blank", examples=["about:blank"])
    title: str = Field(examples=["Действие недоступно в текущем состоянии"])
    status: int = Field(examples=[409])
    detail: str = Field(examples=["действие недоступно в статусе DRAFT"])
    code: str = Field(examples=["INVALID_STATUS"], description="машинный код ошибки")
    errors: list[ValidationIssue] | None = Field(None, description="поля с ошибками (422)")


# ── пользователь, вход, права ────────────────────────────────────────────────────────────────────────────────────


class CompanyLink(Schema):
    inn: str
    name: str


class PersonaCard(Schema):
    """Карточка пользователя для экрана входа простым языком: кто это и чем занимается компания — без сценариев и
    исходов. Права и профиль посчитаны из мира. Поля code, scenario, preview — прежний контракт фронта (SandboxPersonaDto):
    в них те же значок, роль и описание."""
    id: str = Field(examples=["s7"], description="ID для входа")
    badge: str = Field(examples=["ИП"], description="значок роли: ИП, Директор, Участник, Сотрудник, По доверенности, "
                                                     "Специалист банка, Риск-менеджер")
    role_title: str = Field(examples=["Индивидуальный предприниматель"], description="кто этот человек в компании")
    about: str = Field(examples=["Кофейня: 9 сотрудников, гости платят картами, бизнесу 2 года"],
                       description="чем занимается компания (у сотрудника банка — что он делает)")
    code: str = Field(examples=["ИП"], description="то же, что badge (прежнее поле)")
    kind: Literal["client", "bank"]
    full_name: str = Field(examples=["Анна Смирнова"])
    inn: str = Field(description="ИНН основной компании: по нему открывается кабинет", examples=["770100000079"])
    organization: str
    scenario: str = Field(description="то же, что role_title (прежнее поле)")
    permissions: str
    profile: str
    registries: str = Field(description="отвечают ли источники; находки реестров на экране входа не раскрываются")
    preview: str = Field(description="то же, что about (прежнее поле)")
    login_label: str
    role: str = Field(description="client · loan_officer · risk_manager")
    person_inn: str | None = None
    company_inn: str | None = None
    companies: list[CompanyLink] = []
    faults: list[dict[str, Any]] = Field([], description="отказы источников, которые включаются при входе")
    custom: bool = Field(False, description="своя компания, а не пользователь мира")


class ActorView(Schema):
    kind: Literal["client", "bank"]
    inn: str | None
    name: str


class WhyItem(Schema):
    right: str = Field(description="view · prepare · sign · approve")
    allowed: bool
    because: str
    norm: str | None = Field(None, description="норма закона или договор, на котором основано право")


class Rights(Schema):
    roles: list[dict[str, Any]] = Field(description="роли человека в компании: owner, eio, participant, bank_access…")
    can: dict[str, bool] = Field(description="view · prepare · sign · approve", examples=[{"view": True, "prepare": True,
                                                                                        "sign": True, "approve": False}])
    sign_mode: str | None = Field(None, description="self · independent · joint")
    why: list[WhyItem]


class MeCompany(Rights):
    inn: str
    name: str | None = None
    loaded: bool = Field(description="данные компании уже собраны")
    segment: str | None = Field(None, description="IP · LLC · JSC")
    okved: str | None = None
    bank_access: str | None = Field(None, description="уровень доступа в ДБО")


class LoginResult(Schema):
    token: str = Field(description="JWT для заголовка Authorization: Bearer …")
    token_type: Literal["Bearer"]
    persona: PersonaCard
    actor: ActorView
    companies: list[MeCompany]
    loading: bool = Field(description="банк ещё собирает данные компаний — повторить GET /me через пару секунд")


class Me(Schema):
    persona: PersonaCard
    actor: ActorView
    companies: list[MeCompany]
    active_company_inn: str | None
    loading: bool


class ActiveCompany(Schema):
    active_company_inn: str


class StatusOk(Schema):
    status: str = Field(examples=["ok"])


# ── заявка ───────────────────────────────────────────────────────────────────────────────────────────────────────


class Rate(Schema):
    total: str = Field(description="ставка, % годовых", examples=["17.0"])
    key_rate: str = Field(description="ключевая ставка Банка России", examples=["14.0"])
    industry: str = Field(description="отраслевой спред раздела ОКВЭД", examples=["0.0"])
    risk: str = Field(description="спред за класс риска", examples=["3.0"])
    risk_class: Literal["A", "B", "C", "D"]
    section: str | None = Field(None, description="раздел ОКВЭД 2")
    bucket: str | None = Field(None, description="short — до года, long — дольше")
    security: str | None = Field(None, description="none · owner_guarantee · guarantor · collateral")


class Offer(Schema):
    product: Product
    product_name: str
    amount: Money = Field(examples=["400000.00"])
    term_months: int
    payment: Money = Field(description="платёж в месяц", examples=["5666.67"])
    repayment: str = Field(description="annuity · revolving · bullet · seasonal")
    rate: Rate
    binding_cap: str | None = Field(None, description="какое ограничение определило сумму")
    variant: int | None = Field(None, description="номер принятого варианта")


class Reason(Schema):
    code: str = Field(examples=["STOP_TAX_DEBT"])
    kind: str = Field(description="stop · policy · score · manual · ask · cap…")
    text: str


class Contribution(Schema):
    factor: str = Field(examples=["F2_inflow_stability"])
    value: Any = Field(description="значение факта; null — неизвестно")
    points: int
    reason: str
    effect: Literal["plus", "neutral", "minus", "unknown"] | None = None


class Risk(Schema):
    score: int
    pd: float = Field(description="вероятность дефолта за 12 месяцев")
    class_: Literal["A", "B", "C", "D"] = Field(alias="class")
    best_class: Literal["A", "B", "C", "D"] = Field(description="класс при лучших значениях неизвестных факторов")
    contributions: list[Contribution]
    missing: list[str]
    weak: list[str] = Field(description="три самых отрицательных вклада — причины и рычаги K3")


class Decision(Schema):
    """Решение движка: исход, оферта и её варианты, причины, скоринг, трасса правил."""
    outcome: Outcome
    status: str = Field(description="в какой статус переводит заявку")
    offer_kind: Literal["AS_REQUESTED", "COUNTER", "CONDITIONAL"] | None
    offer: Offer | None
    alternatives: list[Offer] = []
    counter: list[str] = Field([], description="что изменено во встречном предложении: AMOUNT · TERM · PRODUCT")
    conditions: list[str] = Field([], description="GUARANTEE · COLLATERAL")
    asks: list[str] = Field([], description="что запросить у клиента: REQ_CORP_APPROVAL, REQ_DOCUMENTS…")
    reasons: list[Reason]
    risk: Risk | None = None
    caps: list[dict[str, Any]] | None = Field(None, description="ограничения суммы: обороты, платёжеспособность, "
                                                    "максимум продукта")
    hints: list[str] = Field([], description="некредитные альтернативы: лизинг, факторинг, гарантия")
    flags: list[str] = []
    trace: list[dict[str, Any]] = Field([], description="шаги вывода для аудита и «почему так»")
    policy_version: str
    mode: str | None = None
    kind: str | None = Field(None, description="вид отказа: STOP · POLICY · SCORE")


class Deadline(Schema):
    status: Status
    at: str = Field(description="до когда действует статус, ISO 8601")
    then: Status = Field(description="куда перейдёт заявка по истечении")


class Signers(Schema):
    mode: str = Field(description="self · independent · joint")
    any_of: list[str] = Field(description="ИНН тех, кто может подписать один")
    required: list[str] = Field(description="ИНН тех, кто должен подписать вместе")


class Signature(Schema):
    inn: str
    fio: str
    role: str
    at: str


class Participant(Schema):
    inn: str
    fio: str
    share: float


class Vote(Schema):
    inn: str
    fio: str | None = None
    vote: Literal["for", "against"]


class Approval(Schema):
    """Согласие участников на крупную сделку (14-ФЗ ст. 46 п. 3): голос — по доле, решение — больше половины всех голосов."""
    status: str = Field(description="open · approved · rejected")
    method: str = Field(description="electronic · notary · shareholders")
    participants: list[Participant]
    votes: list[Vote]
    for_pct: float
    against_pct: float
    threshold_pct: float


class BankNote(Schema):
    at: str
    by: str
    action: str
    comment: str | None = None
    limit: int | None = Field(None, description="полномочия специалиста, ₽")
    offer: Offer | None = None
    second_key: dict[str, Any] | None = Field(None, description="подтверждение риск-менеджера")


class Loan(Schema):
    loan_id: str
    amount: Money
    rate: str
    term_months: int
    status: str = Field(examples=["DISBURSED"])
    disbursed_at: str = Field(description="время выдачи по часам мира")
    number: str | None = Field(None, examples=["КД-2026/DFDC6D"], description="номер кредитного договора")
    product: Product | None = None
    repayment: str | None = Field(None, description="annuity · revolving · bullet · seasonal")
    kind: Literal["loan", "limit"] | None = Field(None, description="loan — деньги на счёте; limit — овердрафт: подключён "
                                                                   "лимит, деньги берутся по мере нужды")


class InfoRequest(Schema):
    asks: list[str]
    from_: str | None = Field(None, alias="from", description="system · bank")
    comment: str | None = None


class ApplicationView(Schema):
    """Заявка целиком: статус, флаги, запрос, решение, оферта и варианты, подписи, выдача и кнопки текущего пользователя."""
    id: str
    company_inn: str
    status: Status
    flags: list[str] = Field(description="бейджи: PROVISIONAL, SOURCE_WAIT, DEGRADED_DATA, RECHECK, SLA_BREACH, DISBURSE_ERROR")
    version: int
    created_at: str
    updated_at: str
    request: dict[str, Any] = Field(description="что просил клиент: product, amount, term_months, goal")
    consent_bki: bool
    created_by: dict[str, Any] | None
    decision: Decision | None
    offer: Offer | None = Field(description="принятая или предложенная оферта")
    offers: list[Offer] = Field(description="основной вариант и альтернативы для выбора")
    info_request: InfoRequest | None
    signers: Signers | None
    signatures: list[Signature]
    approval: Approval | None
    pending_decision: BankNote | None = Field(description="одобрение специалиста ждёт второго ключа")
    bank_decision: BankNote | None
    loan: Loan | None
    final_check: dict[str, Any] | None
    deadline: Deadline | None
    sla_until: str | None = Field(description="до когда специалист должен рассмотреть заявку")
    available_actions: list[Action] = Field(description="кнопки, которые этот пользователь может нажать сейчас")


class EventAuthor(Schema):
    kind: Literal["client", "bank", "system"]
    name: str | None = Field(examples=["Анна Смирнова"], description="человек по имени; у шагов конвейера и сроков — «Банк»")
    role: str | None = Field(None, description="у сотрудника банка: loan_officer · risk_manager")
    title: str | None = Field(None, description="у сотрудника банка: должность")
    detail: str | None = Field(None, description="у шагов банка: проверка данных, автоматическое решение, истёк срок")


class ApplicationEvent(Schema):
    id: int
    at: str = Field(description="время по часам мира симулятора")
    type: str = Field(examples=["application.status_changed"])
    actor: str = Field(examples=["client:770100000079"], description="техническая метка автора")
    payload: dict[str, Any]
    by: EventAuthor | None = Field(None, description="кто сделал шаг — для истории заявки")


class ExplainFactor(Contribution):
    title: str = Field(description="название фактора")
    text: str | None = Field(description="текст причины — только если фактор снижает балл")
    fact: str
    bins: list[dict[str, Any]] = Field(description="интервалы карты и баллы")
    source: str
    next: dict[str, Any] | None = Field(description="до какого значения подтянуть фактор и сколько баллов это даст")


class Explanation(Schema):
    """«Почему так»: скоринг с вкладами и интервалами, ставка из частей, лимит из ограничений, путь к одобрению (K3)."""
    outcome: Outcome
    status: str
    policy_version: str
    reasons: list[Reason]
    scoring: dict[str, Any] = Field(description="score, pd, risk_class, best_class, base, classes, pd_scale, factors[], "
                                                "missing[]")
    price: dict[str, Any] | None = Field(description="ставка: key_rate, industry, risk, total, parts[] с объяснением")
    limit: dict[str, Any] | None = Field(description="caps[] с текстами, binding, amount, class_multiplier")
    path_to_approval: dict[str, Any] = Field(description="changeable, blocked_by[], options[] — рычаги и их результат")


# ── кабинет компании (числа, как в DTO фронта) ───────────────────────────────────────────────────────────────────


class CabinetUser(Schema):
    """Кто работает в кабинете (DemoPersonaDto)."""
    inn: str
    first_name: str
    last_name: str
    initials: str
    organization_name: str
    user_id: str
    role: str
    person_inn: str | None
    today: str = Field(description="сегодня по часам мира симулятора — для приветствия и подписей «сегодня»")


class SummaryCard(Schema):
    """Карточка главной (DashboardSummaryCardDto). У сотрудника банка — очередь, второй ключ и выдачи за день."""
    id: str
    type: Literal["balance", "outflow", "inflow"]
    title: str
    amount: float
    currency: str = Field(examples=["RUB"])
    description: str
    date: str | None = None


class ForecastPoint(Schema):
    date: str
    balance: float


class CashGap(Schema):
    date: str = Field(description="самая глубокая точка ниже нуля")
    amount: float
    first_negative_date: str | None = None


class ForecastOperation(Schema):
    id: str
    date: str
    title: str
    amount: float


class CashForecast(Schema):
    """K1: прогноз остатка по дням, разрыв и платежи, которые к нему ведут."""
    status: Literal["CASH_GAP", "COVERED", "HEALTHY"] = Field(
        description="CASH_GAP — не хватит денег; COVERED — минус в пределах подключённого овердрафта; HEALTHY — всё в порядке")
    credit_line: float | None = Field(None, description="лимит подключённого овердрафта, ₽")
    horizon_days: int
    currency: str
    points: list[ForecastPoint]
    cash_gap: CashGap | None
    operations: list[ForecastOperation]
    daily_inflow: float | None = None
    regular_outflows: list[dict[str, Any]] = []


class CreditProductCard(Schema):
    """Предодобренный продукт (CreditProductDto, K2)."""
    id: str
    name: str
    amount: float = Field(description="доступный лимит")
    currency: str
    rate: float
    is_rate_from: bool = Field(description="ставка «от» — пока нет полного отчёта БКИ")
    term_months: int
    benefits: list[str]
    is_preliminary: bool
    is_recommended: bool = Field(description="закрывает найденный кассовый разрыв")
    product: Product | None = None
    label: str | None = Field(None, description="PREAPPROVED · CONDITIONAL")
    payment: float | None = Field(None, description="платёж в месяц; у овердрафта — проценты, если занят весь лимит")
    conditions: list[str] = []
    cover: dict[str, Any] | None = Field(None, description="у предложения под разрыв: amount — сколько взять, days — на сколько "
                                                         "дней, interest — проценты за эти дни, ₽")
    application_id: str | None = Field(None, description="у предложения под разрыв: заявка на этот продукт уже идёт — "
                                                         "открыть её, а не заводить вторую")


class MatchOption(Schema):
    """Продукт в подборе от задачи — для этой компании: доступен ли, сколько, на каких условиях, что понадобится."""
    product: Product
    name: str
    repayment: str
    available: bool = Field(description="false — продукт этой компании не дать: причина в why")
    label: str = Field(description="PREAPPROVED · CONDITIONAL · REVIEW · UNAVAILABLE")
    outcome: Outcome
    max_amount: Money | None = Field(description="сколько максимум по данным банка")
    offer: dict[str, Any] | None = Field(description="условия на нужную сумму: amount, term_months, rate, payment, repayment")
    counter: list[str] = Field(description="что пришлось изменить: AMOUNT · TERM · PRODUCT")
    needs: list[dict[str, str]] = Field(description="что понадобится: code и текст")
    why: list[str] = Field(description="почему нет или почему так — тексты причин")
    causes: list[dict[str, Any]] = Field(description="те же причины с кодом: code, kind (stop · policy · cap · score · manual), "
                                                     "text — для иконок и подсветки")
    recommended: bool


class PreviewCause(Schema):
    code: str
    kind: str | None = None
    text: str
    fields: list[str] = Field(description="ответы конструктора, от которых зависит причина: industry, loans, delays, "
                                          "flags.tax_debt… — фронт подсвечивает сам ответ, а не пишет текст")


class PreviewProduct(Schema):
    product: Product
    name: str
    available: bool
    label: str = Field(description="PREAPPROVED · CONDITIONAL · REVIEW · UNAVAILABLE")
    max_amount: float | None = Field(description="сколько максимум по данным банка, ₽ (числом — для экрана)")
    rate: float | None = Field(description="личная ставка, % годовых")
    payment: float | None = Field(description="платёж в месяц на максимальную сумму, ₽")
    why: list[PreviewCause]
    needs: list[dict[str, str]]
    recommended: bool


class PersonaPreview(Schema):
    """Что банк скажет о такой компании до создания или правки: тот же генератор, те же факты, скоринг и подбор, что
    у созданной компании, только без сохранения. Меняется ответ — меняется картина, причины указывают на ответы."""
    form: str
    company: dict[str, Any] = Field(description="name, about, okved, okved_name, inflow_avg, debt_load, age_months, headcount")
    path: dict[str, Any] = Field(description="structure, sign_mode (self · independent · joint) и means — кто подписывает "
                                             "и кто одобряет крупную сделку, с нормой")
    people: list[dict[str, Any]] = Field(description="люди компании, как они появятся на экране входа: badge, full_name, "
                                                     "role_title, permissions")
    score: dict[str, Any] = Field(description="score, class и factors[] {factor, title, effect, points, fields}")
    blockers: list[PreviewCause]
    products: list[PreviewProduct]
    recommended: str | None
    assumes: str = Field(description="consent_bki — картина как при подаче заявки, с согласием на запрос кредитной истории")


class PersonaDeleted(Schema):
    deleted: list[str] = Field(description="id пользователей, которых больше нет: своя компания уходит со всеми её людьми")


class Offers(Schema):
    """Подбор от задачи: продукты компании с личными условиями; стоп-факторы — в blockers."""
    inn: str
    goal: str | None
    amount: float | None = Field(description="сколько нужно; для кассового разрыва без суммы — сумма разрыва")
    term_months: int | None
    bki_known: bool = Field(description="есть ли полный отчёт БКИ: без него условия предварительные")
    blockers: list[Reason] = Field(description="стоп-факторы компании: пока они есть, кредита не будет")
    options: list[MatchOption]
    recommended: Product | None


class Insights(Schema):
    inn: str
    cash_forecast: CashForecast | None
    offer: CreditProductCard | None
    contract: dict[str, Any] | None = Field(None, description="K5: госконтракт в ЕИС (reg_num, customer, price, advance_percent, "
                                                              "end_date) и кредит на его исполнение (offer)")


class ScoreFactor(Contribution):
    title: str
    text: str | None


class Score(Schema):
    """Кредитное здоровье до заявки: балл, PD, класс, вклады факторов и рычаги."""
    inn: str
    bki_known: bool
    score: int
    pd: float
    class_: Literal["A", "B", "C", "D"] = Field(alias="class")
    best_class: str
    contributions: list[ScoreFactor]
    missing: list[str]
    weak: list[str]
    base: int
    classes: list[dict[str, Any]]
    levers: list[dict[str, Any]] = Field(description="фактор → до какого значения подтянуть и сколько баллов это даст")


class CompanyProfile(Schema):
    """Что банк знает о компании (CompanyProfileDto) и откуда."""
    inn: str
    name: str | None
    legal_form: str | None
    registered_at: str | None
    activity: dict[str, Any] | None
    tax_regime: str | None
    monthly_revenue: float | None
    currency: str
    sources: list[str]
    updated_at: str | None
    msp_category: int | None
    headcount: int | None
    facts: dict[str, Any] = Field(description="все факты компании")
    source_details: list[dict[str, Any]] = Field(description="источник, статус, дата получения, свежесть")


class RepaymentPlan(Schema):
    """K4: фиксированный график против доли поступлений на истории счёта клиента, стресс-тест на трёх худших месяцах."""
    inn: str
    amount: float
    rate: float
    term_months: int
    fixed: dict[str, Any] = Field(description="payment, total_interest, worst3_inflow_avg, worst3_share, comfortable")
    from_inflows: dict[str, Any] = Field(description="share, min_payment, months, total_interest, max_payment, min_paid")
    recommendation: Literal["fixed", "from_inflows"]
    why: str
    stress_max: float = Field(description="порог: доля поступлений худших месяцев, выше которой фиксированный платёж неудобен")


class Task(Schema):
    id: str
    type: str = Field(description="SIGNATURE · DOCUMENT_REQUEST · OFFER · DRAFT · REVIEW · CONFIRM")
    action: Action
    title: str
    due_date: str | None
    application_id: str
    company_inn: str
    status: Status


class SummaryItem(Schema):
    id: str
    product_name: str
    amount: float
    currency: str
    status: FrontStatus
    status_detail: Status
    flags: list[str]
    updated_at: str


class ApplicationsSummary(Schema):
    applications: list[SummaryItem]
    tasks: list[Task] = Field(description="подписать и ответить — для виджета главной")
    all_tasks: list[Task]


class Dashboard(Schema):
    company: dict[str, Any] | None
    total_balance: Money | None
    monthly_income: Money | None
    monthly_expenses: Money | None
    active_loans_count: int
    cash_flow: list[dict[str, Any]]
    current_month: dict[str, Any] | None = None
    recent_transactions: list[dict[str, Any]]
    offer: dict[str, Any] | None = Field(description="предложение в 1 клик")
    as_of: str | None = None


# ── каталог и калькулятор ────────────────────────────────────────────────────────────────────────────────────────


class Catalog(Schema):
    policy_version: str
    key_rate: dict[str, Any]
    goals: dict[str, Any]
    products: dict[str, Any]
    sections: dict[str, Any]
    alternatives: dict[str, Any]


class ProductCard(Schema):
    """Продукт для витрины и лендинга: цифры из той же политики, что и решения (ставка «от» = КС + отрасль + риск)."""
    id: Product
    name: str
    benefits: list[str]
    amount_min: float
    amount_max: float
    term_months_min: int
    term_months_max: int
    rate_from: float = Field(description="лучшая ставка: ключевая + минимальный отраслевой спред + спред класса A, % годовых")
    rate_parts: dict[str, float] = Field(description="key_rate, industry, risk — из чего сложилась ставка «от»")
    repayment: str
    decision: Literal["auto", "specialist"] = Field(description="кто решает при хорошем классе риска")
    decision_text: str
    goals: list[str] = Field(description="под какие задачи клиента подходит")
    law: str | None = None


class ProductCatalog(Schema):
    policy_version: str
    key_rate: dict[str, Any]
    products: list[ProductCard]


class LoanCalc(Schema):
    rate: str
    rate_parts: dict[str, Any] | None
    repayment: str = Field(description="annuity · revolving · bullet · seasonal")
    payment: Money = Field(description="платёж в месяц; у овердрафта — проценты, если весь лимит занят весь месяц")
    overpayment: Money | None = Field(description="проценты за весь срок; у овердрафта null — платят за занятые дни")
    schedule: list[dict[str, Any]]
    usage_example: dict[str, Any] | None = Field(None, description="у овердрафта: amount, days, interest, text — сколько "
                                                                 "стоит взять сумму на несколько дней")


# ── банк ─────────────────────────────────────────────────────────────────────────────────────────────────────────


class QueueItem(Schema):
    id: str
    inn: str
    status: Status
    flags: list[str]
    request: dict[str, Any]
    reasons: list[Reason]
    proposal: Offer | None = Field(description="что предложил бы движок")
    risk: Risk | None
    pending_decision: BankNote | None
    available_actions: list[Action]
    sla_until: str | None
    updated_at: str


class BankApplication(Schema):
    """Заявка в реестре банка: кто решал, что предложено, класс риска — досье открывается по id."""
    id: str
    inn: str
    company_name: str
    status: Status
    flags: list[str]
    request: dict[str, Any] | None
    outcome: Outcome | None = Field(description="исход движка")
    decided_by: Literal["engine", "bank"] | None = Field(description="решил движок сам или специалист")
    offer: Offer | None
    score: int | None
    risk_class: str | None
    loan: Loan | None
    created_at: str
    updated_at: str


class Percentiles(Schema):
    count: int = Field(description="сколько замеров")
    p50: float | None = Field(description="медиана, с")
    p95: float | None = Field(description="95-й перцентиль, с")
    target: float | None = Field(description="цель (docs/07 §8), с")
    within_target: float | None = Field(description="доля замеров в пределах цели")


class BankMetrics(Schema):
    """Как работает конвейер: сквозная обработка, время до решения и ручного рассмотрения против целей, исходы, выдачи."""
    applications: int
    by_status: dict[str, int]
    decisions: dict[str, Any] = Field(description="auto · manual · stp_share — доля решённых без специалиста")
    time_to_decision: Percentiles = Field(description="от подачи до первого решения: оферта, отказ, дозапрос или специалист")
    manual_review: Percentiles = Field(description="у специалиста: от попадания в очередь до решения")
    outcomes: dict[str, int] = Field(description="исходы движка: APPROVE, COUNTER_OFFER, REQUEST_INFO, MANUAL_REVIEW, REJECT…")
    issued: dict[str, Any] = Field(description="count и amount выданных кредитов")
    sla_breaches: int


class AuditCheck(Schema):
    """Проверка журнала: цепочка хэшей пересчитана с первой записи — правка или удаление любой записи видны."""
    events: int = Field(description="сколько записей проверено")
    intact: bool
    broken_at: int | None = Field(description="номер первой записи, где цепочка не сходится")
    last_hash: str | None


class Dossier(Schema):
    application: ApplicationView
    facts: dict[str, Any]
    sources: list[dict[str, Any]]
    events: list[ApplicationEvent]


# ── симулятор ────────────────────────────────────────────────────────────────────────────────────────────────────


class Preset(Schema):
    key: str
    inn: str
    name: str
    okved: list[str]
    scenario: dict[str, Any] | None


class FaultView(Schema):
    id: str
    source: str
    mode: str
    inn: str | None = Field(None, description="только для этой компании; нет — для всех")


class WorldEvent(Schema):
    event: str
    inn: str
    sources: list[str]
    recheck: bool


class Clock(Schema):
    offset_s: int
    now: str
    today: str


class WorkerState(Schema):
    paused: bool


class PersonaOptions(Schema):
    """Вопросы конструктора своей компании простым языком и что значит каждый ответ."""
    forms: list[dict[str, Any]]
    industries: list[dict[str, Any]] = Field(description="чем занимается: id, title, okved, okved_name, seasonality, channel")
    structures: list[dict[str, Any]] = Field(description="как устроена: id, title, means — кто подписывает и кто одобряет "
                                                         "крупную сделку, с нормой; forms")
    people: list[dict[str, Any]] = Field(description="кто ещё работает в кабинете: бухгалтер, представитель по МЧД")
    choices: dict[str, list[dict[str, Any]]] = Field(description="ответы на вопросы: seasonality, stability, trend, channel, "
                                                                 "loans, delays — id и title")
    groups: list[dict[str, Any]]
    flags: list[dict[str, Any]] = Field(description="особенности фактами: id, group, title, effect, forms")
    params: list[dict[str, Any]] = Field(description="точные цифры, если нужны: id, type, default, description, ge/le")


class ScenarioStep(Schema):
    n: int
    user: dict[str, Any] | None = Field(description="кем войти: id, full_name, code; null — шаг делает система или мир")
    action: str = Field(description="create · submit · run · vote · accept · decline · sign · answer · withdraw · bank · "
                                    "confirm · event · forbidden")
    title: str = Field(description="что сделать, по-русски")
    button: str | None = Field(description="какую кнопку из available_actions нажать")
    api: dict[str, Any] = Field(description="тот же шаг через API: method, path, body")
    expect_status: Status | None = Field(description="статус заявки после шага")
    expect_http: int = Field(description="ожидаемый HTTP-код: 403 — действие этому пользователю запрещено")
    note: str


class Scenario(Schema):
    """Сценарий со сменой ролей: кто по очереди что делает и какой статус ожидать после каждого шага."""
    id: str
    title: str
    about: str
    company: dict[str, Any]
    users: list[str] = Field(description="кто участвует, в порядке появления")
    steps: list[ScenarioStep]


class Health(Schema):
    status: str
    policy: str | None = None


# именованные ответы — так их видно в Swagger и ReDoc
def _named(name: str, model) -> type[Envelope]:
    return type(name, (Envelope[model],), {"__doc__": model.__doc__ or ""})


PersonaCardsResponse = _named("PersonaCardsResponse", list[PersonaCard])
PersonaCardResponse = _named("PersonaCardResponse", PersonaCard)
PersonaPreviewResponse = _named("PersonaPreviewResponse", PersonaPreview)
PersonaDeletedResponse = _named("PersonaDeletedResponse", PersonaDeleted)
LoginResponse = _named("LoginResponse", LoginResult)
MeResponse = _named("MeResponse", Me)
RightsResponse = _named("RightsResponse", Rights)
ActiveCompanyResponse = _named("ActiveCompanyResponse", ActiveCompany)
StatusResponse = _named("StatusResponse", StatusOk)
ApplicationResponse = _named("ApplicationResponse", ApplicationView)
ApplicationsResponse = _named("ApplicationsResponse", list[ApplicationView])
EventsResponse = _named("EventsResponse", list[ApplicationEvent])
ExplanationResponse = _named("ExplanationResponse", Explanation)
CabinetUserResponse = _named("CabinetUserResponse", CabinetUser)
SummaryCardsResponse = _named("SummaryCardsResponse", list[SummaryCard])
InsightsResponse = _named("InsightsResponse", Insights)
OffersResponse = _named("OffersResponse", Offers)
ProductsResponse = _named("ProductsResponse", list[CreditProductCard])
ScoreResponse = _named("ScoreResponse", Score)
ProfileResponse = _named("ProfileResponse", CompanyProfile)
TasksResponse = _named("TasksResponse", list[Task])
RepaymentResponse = _named("RepaymentResponse", RepaymentPlan)
ApplicationsSummaryResponse = _named("ApplicationsSummaryResponse", ApplicationsSummary)
DashboardResponse = _named("DashboardResponse", Dashboard)
CatalogResponse = _named("CatalogResponse", Catalog)
LoanCalcResponse = _named("LoanCalcResponse", LoanCalc)
ProductCatalogResponse = _named("ProductCatalogResponse", ProductCatalog)
QueueResponse = _named("QueueResponse", list[QueueItem])
BankApplicationsResponse = _named("BankApplicationsResponse", list[BankApplication])
DossierResponse = _named("DossierResponse", Dossier)
DecisionResponse = _named("DecisionResponse", Decision)
PresetsResponse = _named("PresetsResponse", list[Preset])
FaultResponse = _named("FaultResponse", FaultView)
FaultsResponse = _named("FaultsResponse", list[FaultView])
WorldEventResponse = _named("WorldEventResponse", WorldEvent)
ClockResponse = _named("ClockResponse", Clock)
WorkerResponse = _named("WorkerResponse", WorkerState)
PersonaOptionsResponse = _named("PersonaOptionsResponse", PersonaOptions)
HealthResponse = _named("HealthResponse", Health)
ScenariosResponse = _named("ScenariosResponse", list[Scenario])
BankMetricsResponse = _named("BankMetricsResponse", BankMetrics)
AuditCheckResponse = _named("AuditCheckResponse", AuditCheck)

ERRORS = {
    401: "Нужен вход: токен битый, истёк или пользователя больше нет (TOKEN_INVALID, LOGIN_REQUIRED, USER_UNKNOWN)",
    403: "Нет права: в этой компании (FORBIDDEN с why и нормой закона), только для банка (BANK_ONLY) или риск-менеджера "
         "(ROLE_REQUIRED), голосуют участники (NOT_A_PARTICIPANT)",
    404: "Нет такого ресурса (APPLICATION_NOT_FOUND, COMPANY_NOT_FOUND, PERSONA_NOT_FOUND, USER_NOT_FOUND…)",
    409: "Действие недоступно сейчас: статус (INVALID_STATUS с app_status), данные компании ещё собираются (COMPANY_NOT_LOADED), "
         "ждём свежий реестр (SOURCE_WAIT), кредитную историю (BKI_PENDING), второй ключ (AWAITING_SECOND_KEY)…",
    422: "Ошибка в данных запроса (VALIDATION_ERROR с errors[], INN_INVALID с suggested_inn, FLAG_UNKNOWN…)",
}


def doc(model=None, *errors: int, summary: str, status: int = 200, description: str | None = None) -> dict:
    """Аргументы декоратора ручки: краткое имя, схема успешного ответа и возможные ошибки."""
    responses: dict = {code: {"model": ProblemDetails, "description": ERRORS[code]} for code in errors}
    if model is not None:
        responses[status] = {"model": model, "description": "успех"}
    out = {"summary": summary, "responses": responses}
    if description:
        out["description"] = description
    return out
