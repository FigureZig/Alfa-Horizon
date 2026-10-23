"""Сценарии ролей: кто что делает с заявкой и как после этого меняется статус. Один источник для сквозного теста
(tests/e2e/test_flows.py прокликивает их через HTTP API с перелогином) и для документа docs/15_roles.md.

Пользователи — из seed/personas.yaml и люди мира без сценария (u-<ключ>); «system» — конвейер и выдача (worker).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    user: str                    # id пользователя или "system"
    action: str                  # create · submit · run · vote · accept · decline · sign · answer · withdraw · bank · confirm ·
    arg: object = None           # event · forbidden (действие, которое этому пользователю делать нельзя)
    status: str | None = None    # статус заявки после шага
    note: str = ""


@dataclass(frozen=True)
class Flow:
    id: str
    title: str
    company: str                 # ключ компании в seed/personas.yaml
    about: str
    steps: list[Step]
    request: dict = field(default_factory=dict)    # пусто — запрос из scenario.request компании


FLOWS = [
    Flow("large-deal", "Крупная сделка: участники голосуют «за»", "masterstroy",
         "ООО из трёх участников просит 6 млн ₽ — больше 25% активов, согласие даёт общее собрание (14-ФЗ ст. 46 п. 3). "
         "Устав позволяет электронные бюллетени (ст. 38 п. 2), голос — по доле (ст. 32 п. 1), нужно больше половины "
         "голосов всех участников (ст. 37 п. 7).",
         [Step("s2", "create", status="DRAFT", note="директор Кравец готовит заявку"),
          Step("s2", "submit", status="SUBMITTED"),
          Step("system", "run", status="INFO_REQUESTED", note="крупная сделка — открыто голосование участников"),
          Step("u-li", "vote", "for", status="INFO_REQUESTED", note="Ли «за»: 35% — ещё не большинство"),
          Step("s2", "vote", "for", status="CHECKING", note="Кравец «за»: 75% — согласие есть, проверка заново"),
          Step("system", "run", status="OFFERED"),
          Step("s2", "accept", status="SIGNING"),
          Step("s2", "sign", status="SIGNED"),
          Step("system", "run", status="ISSUED", note="финальная проверка, АБС, деньги на счёте")]),
    Flow("large-deal-against", "Крупная сделка: участники против", "masterstroy",
         "Те же 6 млн ₽, но двое участников голосуют «против» — согласие уже недостижимо, банк заявку закрывает: "
         "сделка без согласия была бы оспоримой (ГК ст. 173.1).",
         [Step("s2", "create", status="DRAFT"),
          Step("s2", "submit", status="SUBMITTED"),
          Step("system", "run", status="INFO_REQUESTED"),
          Step("u-li", "vote", "against", status="INFO_REQUESTED", note="«против» 35%"),
          Step("u-morozov", "vote", "against", status="WITHDRAWN", note="«против» 60% — большинства «за» не будет")]),
    Flow("prepare-and-sign", "Бухгалтер готовит, директор подписывает", "lenta",
         "У Иванова в «Лента-Опт» доступ в ДБО с правом подготовки: он подаёт заявку и принимает оферту, "
         "но подписать не вправе — подписывает директор по ЕГРЮЛ (14-ФЗ ст. 40 п. 3, ГК ст. 53).",
         [Step("r8", "create", status="DRAFT", note="Иванов готовит заявку в ДБО компании"),
          Step("r8", "submit", status="SUBMITTED"),
          Step("system", "run", status="OFFERED"),
          Step("r8", "accept", status="SIGNING", note="отправляет на подпись"),
          Step("r8", "forbidden", "sign", status="SIGNING", note="подписать сам не может — 403"),
          Step("r12", "sign", status="SIGNED", note="директор Захаров подписывает"),
          Step("system", "run", status="ISSUED")],
         request={"product": "WORKING_CAPITAL", "amount": 3_000_000, "term_months": 24, "goal": "stock"}),
    Flow("second-key", "Выше полномочий специалиста: второй ключ", "sklad",
         "Инвестиционный кредит идёт к специалисту: в ЕГРЮЛ директор Никитин, а в анкете банка — Фомин. Специалист одобряет "
         "18 млн ₽ — это выше его порога 15 млн, решение подтверждает риск-менеджер. Подписывает директор по реестру.",
         [Step("r8", "forbidden", "create", note="Иванов здесь только участник с просмотром в ДБО — заявку не подаёт"),
          Step("u-fomin", "create", status="DRAFT", note="Фомин — полный доступ в ДБО"),
          Step("u-fomin", "submit", status="SUBMITTED"),
          Step("system", "run", status="UNDER_REVIEW", note="расхождение данных и продукт со специалистом"),
          Step("bank", "bank", "approve", status="UNDER_REVIEW", note="специалист одобряет 18 млн ₽ — ждёт второй ключ"),
          Step("bank", "forbidden", "confirm", status="UNDER_REVIEW", note="подтвердить своё же решение нельзя"),
          Step("risk", "confirm", True, status="OFFERED", note="риск-менеджер ставит второй ключ"),
          Step("u-fomin", "accept", status="SIGNING"),
          Step("u-fomin", "forbidden", "sign", status="SIGNING", note="Фомин не директор по ЕГРЮЛ — 403"),
          Step("u-nikitin", "sign", status="SIGNED", note="подписывает директор Никитин"),
          Step("system", "run", status="ISSUED")]),
    Flow("specialist-asks", "Специалист запрашивает документы", "hleb",
         "12 млн ₽ — выше порога автоматического решения 10 млн: заявка у специалиста. Он просит пояснения, клиент отвечает, "
         "специалист одобряет сам — сумма в пределах его полномочий.",
         [Step("s5", "create", status="DRAFT"),
          Step("s5", "submit", status="SUBMITTED"),
          Step("system", "run", status="UNDER_REVIEW"),
          Step("bank", "bank", "request_info", status="INFO_REQUESTED", note="нужны пояснения к отчётности"),
          Step("s5", "answer", "documents", status="UNDER_REVIEW", note="клиент прикладывает документы"),
          Step("bank", "bank", "approve", status="OFFERED", note="12 млн ₽ — в пределах полномочий специалиста"),
          Step("s5", "accept", status="SIGNING"),
          Step("s5", "sign", status="SIGNED"),
          Step("system", "run", status="ISSUED")]),
    Flow("director-change", "Смена директора во время подписи", "lenta",
         "Директор принял оферту, договор ждёт подписи — и в ЕГРЮЛ появляется запись о новом руководителе. Банк узнаёт об этом "
         "из реестра, останавливает подпись и пересматривает заявку: подписывает тот, кто вправе действовать без доверенности "
         "по ЕГРЮЛ сейчас (14-ФЗ ст. 40 п. 3, ГК ст. 53). Прежний директор подписать уже не может.",
         [Step("r12", "create", status="DRAFT", note="директор Захаров готовит заявку"),
          Step("r12", "submit", status="SUBMITTED"),
          Step("system", "run", status="OFFERED"),
          Step("r12", "accept", status="SIGNING", note="договор ждёт подписи Захарова"),
          Step("system", "event", "egrul.director_changed", status="OFFERED",
               note="в ЕГРЮЛ новый директор — подпись остановлена, полномочия перепроверены, оферта в силе"),
          Step("u-novikova", "accept", status="SIGNING", note="новый директор Новикова принимает оферту"),
          Step("r12", "forbidden", "sign", status="SIGNING", note="Захаров больше не директор по ЕГРЮЛ — 403"),
          Step("u-novikova", "sign", status="SIGNED", note="подписывает новый директор"),
          Step("system", "run", status="ISSUED")],
         request={"product": "WORKING_CAPITAL", "amount": 3_000_000, "term_months": 24, "goal": "stock"}),
    Flow("poa-sign", "Подпись по доверенности (МЧД)", "vector",
         "Финансовый директор Кузнецова не руководитель по ЕГРЮЛ, но у неё действующая машиночитаемая доверенность "
         "с полномочием подписать кредитный договор (ГК ст. 185.1, 63-ФЗ ст. 17.2). Банк проверяет МЧД в реестре ФНС "
         "перед подписью; когда доверенность отзывают, подписать по ней уже нельзя — подписывает директор.",
         [Step("u-kuznetsova", "create", status="DRAFT", note="Кузнецова готовит заявку: доступ в ДБО с правом подготовки"),
          Step("u-kuznetsova", "submit", status="SUBMITTED"),
          Step("system", "run", status="OFFERED"),
          Step("u-kuznetsova", "accept", status="SIGNING"),
          Step("system", "event", "mchd.revoked", status="OFFERED",
               note="доверенность отозвана в реестре МЧД — подпись остановлена, заявка пересмотрена"),
          Step("u-kuznetsova", "accept", status="SIGNING", note="оферта в силе — Кузнецова принимает её снова"),
          Step("u-kuznetsova", "forbidden", "sign", status="SIGNING", note="МЧД отозвана — подписать нельзя, 403"),
          Step("s3", "sign", status="SIGNED", note="подписывает директор Орлов"),
          Step("system", "run", status="ISSUED")],
         request={"product": "WORKING_CAPITAL", "amount": 2_000_000, "term_months": 24, "goal": "stock"}),
    Flow("poa-sign-active", "Подписывает представитель по МЧД", "vector",
         "Та же компания: доверенность действует — финансовый директор подписывает кредитный договор сама, без директора.",
         [Step("u-kuznetsova", "create", status="DRAFT"),
          Step("u-kuznetsova", "submit", status="SUBMITTED"),
          Step("system", "run", status="OFFERED"),
          Step("u-kuznetsova", "accept", status="SIGNING"),
          Step("u-kuznetsova", "sign", status="SIGNED", note="подпись по МЧД: представитель вправе по доверенности"),
          Step("system", "run", status="ISSUED")],
         request={"product": "WORKING_CAPITAL", "amount": 2_000_000, "term_months": 24, "goal": "stock"}),
    Flow("fix-and-return", "Устранимый отказ и путь к одобрению", "romashka",
         "Недоимка 72 тыс. ₽ выше порога политики — отказ с объяснением, что исправить. Компания гасит недоимку (событие "
         "в реестре ФНС), подаёт снова — и получает оферту.",
         [Step("s4", "create", status="DRAFT"),
          Step("s4", "submit", status="SUBMITTED"),
          Step("system", "run", status="REJECTED", note="стоп-фактор: недоимка"),
          Step("system", "event", "fns.tax_debt_paid", status="REJECTED", note="недоимка погашена — в ФНС новые данные"),
          Step("s4", "create", status="DRAFT", note="новая заявка"),
          Step("s4", "submit", status="SUBMITTED"),
          Step("system", "run", status="OFFERED")]),
]

ACTION_TEXT = {
    "create": "создаёт заявку", "submit": "подаёт", "run": "делает свою часть сама — подождите несколько секунд",
    "vote": "голосует", "accept": "принимает оферту",
    "decline": "отказывается от оферты", "sign": "подписывает", "answer": "отвечает на запрос", "withdraw": "отзывает",
    "bank": "решение специалиста", "confirm": "второй ключ", "event": "событие в реестре", "forbidden": "пробует",
}
ARG_TEXT = {"for": "«за»", "against": "«против»", "approve": "одобрить", "reject": "отказать", "request_info": "дозапрос",
            True: "подтвердить", False: "вернуть", "documents": "документами", "fns.tax_debt_paid": "недоимка погашена",
            "egrul.director_changed": "новый директор", "mchd.revoked": "МЧД отозвана",
            "sign": "подписать", "create": "подать заявку", "confirm": "подтвердить"}

ACTION_TEXT_EN = {
    "create": "creates an application", "submit": "submits", "run": "does its part — wait a few seconds", "vote": "votes",
    "accept": "accepts the offer", "decline": "declines the offer", "sign": "signs", "answer": "answers the request",
    "withdraw": "withdraws", "bank": "specialist decision", "confirm": "second key", "event": "register event",
    "forbidden": "tries",
}
ARG_TEXT_EN = {"for": "for", "against": "against", "approve": "approve", "reject": "reject", "request_info": "request info",
               True: "confirm", False: "return", "documents": "with documents", "fns.tax_debt_paid": "tax arrears paid",
               "egrul.director_changed": "new director", "mchd.revoked": "power of attorney revoked", "sign": "to sign",
               "create": "to apply", "confirm": "to confirm"}
EN = {   # английские тексты гида GET /sandbox/scenarios?lang=en: заголовок, описание, заметки по номерам шагов
    "large-deal": {
        "title": "Major transaction: the members vote for it",
        "about": "An LLC with three members asks for ₽6M, more than 25% of its assets, so the general meeting must consent "
                 "(14-FZ art. 46). The charter allows electronic ballots, votes are weighted by share, and more than half of "
                 "all members' votes is needed.",
        "notes": {1: "director Kravets prepares the application", 3: "major transaction — the members' vote is open",
                  4: "Li votes for: 35%, not a majority yet", 5: "Kravets votes for: 75% — consent given, the check reruns",
                  9: "final check, core banking, money on the account"}},
    "large-deal-against": {
        "title": "Major transaction: the members are against",
        "about": "The same ₽6M, but two members vote against — consent can no longer be reached, so the bank closes the "
                 "application: a deal without consent could be contested (Civil Code art. 173.1).",
        "notes": {4: "against: 35%", 5: "against: 60% — there will be no majority for"}},
    "prepare-and-sign": {
        "title": "The accountant prepares, the director signs",
        "about": "Ivanov has online banking access with the right to prepare at Lenta-Opt: he submits the application and "
                 "accepts the offer but may not sign — the director from the register signs (14-FZ art. 40, Civil Code art. 53).",
        "notes": {1: "Ivanov prepares the application in online banking", 4: "sends it for signing",
                  5: "cannot sign himself — 403", 6: "director Zakharov signs"}},
    "second-key": {
        "title": "Above the specialist's authority: the second key",
        "about": "An investment loan goes to the specialist: the register shows director Nikitin, the bank's form shows Fomin. "
                 "The specialist approves ₽18M, above the ₽15M limit, so the risk manager confirms. "
                 "The registered director signs.",
        "notes": {1: "Ivanov is only a view-only member here and cannot apply", 2: "Fomin has full online banking access",
                  4: "data mismatch and the product go to the specialist",
                  5: "the specialist approves ₽18M and waits for the second key",
                  6: "you cannot confirm your own decision", 7: "the risk manager sets the second key",
                  9: "Fomin is not the registered director — 403", 10: "director Nikitin signs"}},
    "specialist-asks": {
        "title": "The specialist requests documents",
        "about": "₽12M is above the ₽10M automatic decision limit, so the application goes to the specialist. They ask for "
                 "explanations, the client answers, and the specialist approves within their own authority.",
        "notes": {4: "explanations of the financial statements are needed", 5: "the client attaches documents",
                  6: "₽12M is within the specialist's authority"}},
    "director-change": {
        "title": "The director changes during signing",
        "about": "The director accepted the offer and the agreement awaits signing when the register records a new director. "
                 "The bank learns it from the register, stops signing and rechecks: whoever may act without a power of attorney "
                 "now signs (14-FZ art. 40, Civil Code art. 53). The former director can no longer sign.",
        "notes": {1: "director Zakharov prepares the application", 4: "the agreement awaits Zakharov's signature",
                  5: "new director in the register — signing stopped, authority rechecked, the offer stands",
                  6: "the new director Novikova accepts the offer", 7: "Zakharov is no longer the registered director — 403",
                  8: "the new director signs"}},
    "poa-sign": {
        "title": "Signing by power of attorney: revoked",
        "about": "CFO Kuznetsova is not the registered director but holds an active machine-readable power of attorney to sign "
                 "the loan agreement (Civil Code art. 185.1, 63-FZ art. 17.2). The bank checks it in the tax service registry "
                 "before signing; once it is revoked, she can no longer sign — the director signs.",
        "notes": {1: "Kuznetsova prepares the application: online banking access with the right to prepare",
                  5: "the power of attorney is revoked — signing stopped, the application rechecked",
                  6: "the offer stands — Kuznetsova accepts it again", 7: "the power of attorney is revoked — cannot sign, 403",
                  8: "director Orlov signs"}},
    "poa-sign-active": {
        "title": "A representative signs by power of attorney",
        "about": "The same company: the power of attorney is active, so the CFO signs the loan agreement herself.",
        "notes": {5: "signed by power of attorney: the representative is authorised"}},
    "fix-and-return": {
        "title": "A fixable decline and the path to approval",
        "about": "₽72K tax arrears are above the policy limit — a decline explaining what to fix. The company pays the arrears "
                 "(an event in the tax register), applies again and gets an offer.",
        "notes": {3: "stop factor: tax arrears", 4: "arrears paid — the tax service has new data", 5: "a new application"}},
}
