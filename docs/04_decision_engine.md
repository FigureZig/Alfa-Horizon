# 04. Движок решения — экспертная система

Ground truth по банковской логике. Схемы: **E1** (алгоритм движка), **D1** (конвейер и исходы). Нормы — `05_legal.md`, параметры и цифры — `10_sources.md`.
Скоринг — `12_scoring.md`: балльная карта с сегментами ИП и ООО/АО за портом `RiskModel` → балл, PD, класс риска A–D, вклады факторов.

## 1. Роль и границы
- **Один движок, два режима.** `commit` — решение по заявке, пишется в БД и в аудит. `simulate` — тот же расчёт на гипотетических фактах без записи:
  предодобрение (U1), оффер K2, контрфакты K3, ценность информации (VOI).
- **Чистая функция** без IO: `decide(facts, policy_version, mode) → Decision`. Данные готовит Worker (снапшоты), движок их только читает.
  Поэтому решение воспроизводимо: те же снапшоты + та же версия политики = тот же результат.
- **Выход:** `outcome`, `offerKind`, условия (`terms`), требования (`conditions[]`), варианты (`alternatives[]`), причины (`reasons[]`), трасса (`trace[]`), запросы данных (`asks[]`).

## 2. Факты
Факт = значение + происхождение + свежесть. Состояние факта — **трёхзначное**: `KNOWN`, `STALE` (снапшот старше TTL), `UNKNOWN` (нет данных или источник недоступен).

| Факт | Источник (поле — `09_data_contracts.md`) | TTL | Критичен для |
|---|---|---|---|
| `company.opf`, `company.status`, `company.okved` | ЕГРЮЛ `@КодОПФ`, `СвСтатус`, `СвОКВЭДОсн` | 24 ч | маршрут правил, подбор, ставка |
| `eio[]` (лицо, режим, недостоверность, дисквалификация) | ЕГРЮЛ `СведДолжнФЛ`, `СвПолном@ВидПолном`, `СвНедДанДолжнФЛ`, `СвДискв`; реестр дисквалифицированных | 24 ч; перед подписью и выдачей — свежий | права, стоп-факторы |
| `participants[]` (лицо, доля) | ЕГРЮЛ `СвУчредит/ДоляУстКап` | 24 ч | крупная сделка, заинтересованность, поручитель |
| `company.assets_total` | ГИР БО `balance.current1600` (в источнике тыс. ₽, адаптер переводит в ₽) | 30 дн. | порог 25% |
| `tax.debt_total`, `msp.category`, `tax.regime` | ФНС `ОбщСумНедоим`, `КатСубМСП`, `СведСНР` | 7–30 дн. | стоп-фактор, продукты |
| `bki.*` (просрочки, нагрузка, банкротство, запросы) | БКИ v3.4 `Credits/Credit`, `Bankruptcy`, `RequestsStatistic` | на заявку | риск, стоп-факторы |
| `poa` (статус, полномочия, срок) | реестр МЧД `status`, `powers[]`, `validTo` | 1 ч; перед подписью — свежий | право подписи представителя |
| `legal.*` (банкротство, суды, перечни) | юр. проверки | 1 дн.; перед выдачей — свежий | стоп-факторы |
| `turnover.*` (средние поступления, стабильность, доля в банке) | банк: транзакции | 1 ч | лимит, K1 |
| `access`, `charter.limits`, `charter.decisionMethod` | банк: ДБО, устав | 1 ч | `prepare`, согласие по уставу |
| `deal.*` (продукт, сумма, срок, цель, обеспечение) | заявка | — | всё |

## 3. База знаний (правила как данные)
Правила лежат в YAML в репозитории (`policy/`); версия политики = имя файла + hash, в БД не копируем — **неизменяемость обеспечивает git**. Виды правил:
`derive` (производный факт, прямой вывод) · `knockout` (стоп-фактор) · `requirement` (нужны подписанты, решение органа, поручитель, согласие) ·
`cap` (ограничение лимита) · `table` (таблица решений) · `outcome` (приоритет исходов).
У каждого правила: `id`, `when`, `then`, `explain` (шаблон текста), `norm` (норма или «политика банка»), `on_unknown` (что делать, если условие нельзя вычислить).

```yaml
policy: "2026.10-1"                 # версия; хранится в каждом решении
rules:
  - id: LARGE_DEAL_LLC
    kind: derive
    when: "company.opf == 'LLC' and deal.exposure >= 0.25 * company.assets_total"
    then: { set: { deal.is_large: true } }
    on_unknown: { company.assets_total: ASSUME_STRICT }      # нет БФО → считаем крупной (строгий вариант)
    norm: "14-ФЗ ст. 46 п. 1"
    explain: "Кредит {deal.exposure} ≥ 25% активов {company.assets_total} → крупная сделка"
  - id: LARGE_DEAL_SOLE_OWNER_EXCEPTION
    kind: derive
    when: "deal.is_large and participants.count == 1 and participants[0].person == eio[0].person"
    then: { set: { deal.corporate_approval_needed: false } }
    norm: "14-ФЗ ст. 46 п. 7"
    explain: "Согласие не требуется: единственный участник — он же единственный ЕИО"
  - id: CORPORATE_APPROVAL
    kind: requirement
    when: "deal.is_large and deal.corporate_approval_needed != false"
    then: { require: CORPORATE_APPROVAL, organ: "by_opf", form: "charter.decisionMethod" }
    norm: "14-ФЗ ст. 46 п. 3; 208-ФЗ ст. 79; ГК ст. 67.1 п. 3 пп. 3"
  - id: JOINT_EIO_SIGNERS
    kind: requirement
    when: "eio.mode == 'joint'"
    then: { require: SIGNERS_ALL_EIO }
    norm: "ГК ст. 53 п. 1; ЕГРЮЛ СвПолном@ВидПолном = 1"
  - id: EIO_DISQUALIFIED
    kind: knockout
    when: "signer.disqualified"
    then: { stop: STOP_EIO_DISQUALIFIED, fixable: true, lever: change_signer }
    on_unknown: { signer.disqualified: WAIT }                # реестр недоступен — ждём, не угадываем
    norm: "КоАП ст. 3.11 ч. 1"
  - id: TAX_DEBT
    kind: knockout
    when: "tax.debt_total > policy.tax_debt_max"
    then: { stop: STOP_TAX_DEBT, fixable: true, lever: pay_tax_debt }
    on_unknown: { tax.debt_total: STALE_OK }                 # данные ФНС помесячные — берём последний снапшот
    norm: "политика банка [наш дизайн]"
tables:
  limit_caps:            # политика срабатывания COLLECT MIN — лимит = минимум из применимых капов
    hit: COLLECT_MIN
    rows:
      - { when: "deal.product == 'OVERDRAFT'", cap: "policy.k_overdraft * turnover.avg_monthly_in", reason: CAP_TURNOVER }
      - { when: "true", cap: "max_principal(payment = policy.p_payment * turnover.avg_monthly_in, deal.term, rate)", reason: CAP_PAYMENT_CAPACITY }
      - { when: "true", cap: "product.max_amount", reason: CAP_PRODUCT_MAX }
  risk_spread:           # UNIQUE — ровно одна строка должна сработать
    hit: UNIQUE
    rows: [ { when: "risk.class == 'A'", spread: 2.0 }, { when: "risk.class == 'B'", spread: 3.0 },     # спред = EL класса + 1,5 п.п. (12 §5)
            { when: "risk.class == 'C'", spread: 5.0 }, { when: "risk.class == 'D'", spread: 11.5 } ]
outcome_priority: [REJECT, REQUEST_INFO, MANUAL_REVIEW, APPROVE_WITH_CONDITIONS, COUNTER_OFFER, APPROVE]
```
Значения спредов и коэффициентов — **наш дизайн**, параметры политики (§9). Нормы закона — только в правилах, которые их реализуют.

**Реализация MVP (`backend/app/domain/engine.py`):** условия правил записаны в коде движка короткими функциями, а все числа, таблицы, продукты, отрасли
и тексты причин — в `backend/policy/*.yaml`. Трасса с нормами и причины остаются. Интерпретатор правил из YAML с логикой Клини — путь роста, если правил станет много.
Как из этого получаются деньги — `13_credit_mechanics.md`.

## 4. Алгоритм вывода (страница E1)
```
decide(facts, policy, mode):
  1. classify(facts)                 -> KNOWN | STALE | UNKNOWN по TTL и состоянию источника
  2. forward_chain(rules)            -> агенда по приоритету (knockout > derive > requirement),
                                        повторяем, пока появляются новые факты (неподвижная точка);
                                        условие с UNKNOWN вычисляется в трёхзначной логике Клини;
                                        если результат UNKNOWN — применяем on_unknown правила (§5)
  3. tables(limit_caps, rate, term)  -> политики срабатывания DMN: UNIQUE, FIRST, COLLECT MIN/MAX/SUM
  4. counter_optimizer(request)      -> основной вариант + до 2 альтернатив внутри политики (§8)
  5. voi(unknown_facts)              -> какие неизвестные меняют исход: спросить или нет (§6)
  6. resolve_outcome(priority)       -> первый подходящий исход из outcome_priority
  7. trace                           -> сработавшие правила, входы, нормы, reason codes, тексты
  8. if mode == commit: событие decision.made (политика, хэш входа, снапшоты) + краткая копия в applications.data
```
Масштаб — десятки правил: полный пересчёт занимает миллисекунды, поэтому пересчитываем целиком. Инкрементальный вывод (Rete [P11]) — путь роста, если правил станут тысячи.

## 5. Неизвестные и устаревшие факты: fallback живёт в базе знаний
Поведение продукта при отказе источника задаётся **политикой факта** в правиле и проверяется тестами так же, как кредитная политика.

| Политика | Что делает движок | Пример |
|---|---|---|
| `STALE_OK` | берёт последний снапшот, ставит флаг `DEGRADED_DATA` | недоимка ФНС (данные помесячные) |
| `WAIT` | шаг ждёт источник до дедлайна (`SOURCE_WAIT`), затем `MANUAL` | дисквалификация директора при недоступном реестре |
| `ASSUME_STRICT` | берёт строгий вариант и объясняет его | нет БФО → сделка крупная → нужно решение участников |
| `ASK` | запрос клиенту (если VOI говорит, что факт меняет исход) | обороты в другом банке для ИП |
| `PROVISIONAL` | предварительная оферта, подпись после получения факта | КИ из БКИ для суммы ≤ порога |
| `BLOCK` | критичный шаг (подпись, выдача) не выполняется без свежего факта | статус МЧД перед подписью представителя |
| `MANUAL` | исход MANUAL_REVIEW с причиной | противоречие источников |
| `IGNORE` | правило не применяется | сигнал ЕИС для K5 |

Полная матрица «факт × сбой → поведение» — `07_resilience.md` §4–5.

## 6. VOI — спрашиваем только то, что меняет решение
```
asks(facts, unknown):
  out = []
  for f in unknown where f.policy == ASK:
      best  = decide(facts | {f: f.best_case},  mode=simulate)   # границы из допустимого диапазона
      worst = decide(facts | {f: f.worst_case}, mode=simulate)
      if best.outcome != worst.outcome or |best.limit - worst.limit| >= policy.voi_min_delta:
          out.append(f, impact = best.limit - worst.limit, effort = f.effort)
  return sorted(out, by impact / effort, desc)     # клиенту — 1–3 самых полезных запроса
```
Если ни один неизвестный факт не меняет исход — дозапроса нет, решение принимается сразу. Теория — [P13].

## 7. K3 — путь к одобрению (контрфакты)
```
LEVERS = amount(−10%…−50%), term(+6…+24 мес.), add_guarantor, add_collateral(v),
         pay_tax_debt, move_turnover(+x%), wait(3 | 6 мес.)            # только то, что клиент может сделать
path_to_approval(facts, target):
  options = []
  for combo in combinations(LEVERS, size ≤ 2) where actionable(combo, facts):
      r = decide(apply(facts, combo), mode=simulate)
      if better(r, current): options.append(combo, r, cost(combo))
  return pareto_top3(options)       # по эффекту (исход, лимит) и «цене» действия для клиента
```
Стоп-факторы с `fixable: false` (банкротство, ликвидация) в рычаги не попадают — текст «изменить нельзя» и альтернатива, если она есть.
Выбранное действие → клон заявки с подставленными изменениями. Основание подхода — контрфактические объяснения [P12].

## 8. Исходы и оптимизатор контрпредложения
Порядок для запроса (продукт P, сумма A, срок T):
1. Стоп-фактор → `REJECT` (категория `STOP_FIXABLE` или `STOP_FINAL`).
2. Нужен факт, меняющий исход → `REQUEST_INFO`; исключение (выше полномочий, пограничный риск, расхождение данных, `MANUAL`) → `MANUAL_REVIEW`.
3. Лимит `L = COLLECT MIN(caps(P, T))`. Если `L ≥ A` и обеспечение не требуется → `APPROVE`.
4. Класс риска требует обеспечения и есть кто или что может его дать → `APPROVE_WITH_CONDITIONS` (GUARANTEE, COLLATERAL); альтернатива — меньшая сумма без обеспечения.
5. `L < A`: ищем минимальный срок `T' ≤ T_max(P)`, при котором `caps(P, T') ≥ A` → `COUNTER_OFFER(TERM)`; иначе `COUNTER_OFFER(AMOUNT)` с `A' = L ≥ A_min`;
   иначе другой кредитный продукт по цели → `COUNTER_OFFER(PRODUCT)`.
6. Ничего не подходит → `REJECT(POLICY)` + K3.

| Исход | Статус | Reason codes (примеры) |
|---|---|---|
| APPROVE | OFFERED · AS_REQUESTED | — |
| COUNTER_OFFER: AMOUNT · TERM · PRODUCT | OFFERED · COUNTER | `CAP_TURNOVER`, `CAP_PAYMENT_CAPACITY`, `CAP_TERM_MAX`, `POL_PRODUCT_FIT` |
| APPROVE_WITH_CONDITIONS: GUARANTEE · COLLATERAL | OFFERED · CONDITIONAL | `REQ_GUARANTOR`, `REQ_COLLATERAL` |
| REQUEST_INFO | INFO_REQUESTED | `REQ_CORP_APPROVAL`, `REQ_CHARTER_APPROVAL`, `DATA_MISSING` |
| MANUAL_REVIEW | UNDER_REVIEW | `POL_AUTHORITY_EXCEEDED`, `POL_BORDERLINE_RISK`, `DATA_CONFLICT`, `DATA_SOURCE_UNAVAILABLE` |
| REJECT: STOP_FIXABLE · STOP_FINAL · POLICY | REJECTED | `STOP_TAX_DEBT`, `STOP_EIO_DISQUALIFIED`, `STOP_EIO_UNRELIABLE`, `STOP_BANKRUPTCY`, `STOP_LIQUIDATION`, `POL_RISK_CLASS`, `POL_BUSINESS_AGE` |

Каждый не-APPROVE исход обязан иметь хотя бы одну причину с текстом — это проверяется тестом.

## 9. Параметры политики (наш дизайн, версия в БД)
| Параметр | Демо-значение | Обоснование |
|---|---|---|
| ставка | КС [M1] + отраслевой спред [M4 − M3] + спред за класс (A 2 · B 3 · C 5 · D 11,5 п.п., D — только после ручного решения) | спред за риск = EL класса + 1,5 п.п. (12 §5) |
| лимит | минимум капов × множитель класса (A 1,0 · B 0,85 · C 0,6 · D 0) | 12 §5 |
| `k_overdraft` | 0,4 × среднемесячных поступлений | наш дизайн |
| `p_payment` | платёж ≤ 0,3 × среднемесячных поступлений | наш дизайн |
| `tax_debt_max` | 50 000 ₽ | ориентир — условие программы «1764» [M7] ⚠️; в политике это параметр |
| `min_business_age` | 6 мес. | наш дизайн |
| `auto_authority_max` | 10 млн ₽ (выше — аналитик) | наш дизайн |
| `provisional_max` | 3 млн ₽ (до суммы — предварительная оферта при недоступном БКИ) | наш дизайн |
| `voi_min_delta` | 10% лимита | наш дизайн |
| сроки (демо / прод) | оферта 10 мин / 10 дн.; дозапрос 5 мин / 7 дн.; подпись 5 мин / 5 дн.; черновик 30 дн. | демо ускорено, значения в конфиге |

## 10. Запись решения
```json
{ "decisionId": "…", "applicationId": "…", "mode": "commit", "policyVersion": "2026.10-1",
  "outcome": "COUNTER_OFFER", "offerKind": "COUNTER", "counter": ["AMOUNT"],
  "terms": { "product": "EXPRESS", "amount": "3200000.00", "currency": "RUB", "termMonths": 24, "rate": "21.40" },
  "alternatives": [ { "amount": "5000000.00", "conditions": ["GUARANTEE"] } ],
  "reasons": [ { "code": "CAP_PAYMENT_CAPACITY", "text": "Платёж по 5 млн превысит 30% поступлений" } ],
  "trace": [ { "rule": "LARGE_DEAL_LLC", "result": false, "inputs": { "deal.exposure": "5000000", "company.assets_total": "42000000" }, "norm": "14-ФЗ ст. 46 п. 1" } ],
  "inputHash": "sha256:…", "snapshotIds": ["egrul:…", "bki:…"], "flags": [] }
```

## 11. Досье и профессиональное суждение
Досье аналитика (B1) собирает входы, на которые банк опирается в профессиональном суждении о финансовом положении заёмщика и качестве обслуживания долга
(590-П п. 3.1, 3.3, 3.7 [L21] 🟡): обороты и их стабильность, налоги и недоимки, отчётность (ГИР БО), КИ (просрочки, платежи), события реестров. Категорию качества и резервы MVP не считает.

## 12. Версии политики и проверка до включения
- Версия неизменяема; активна ровно одна (плюс challenger, если включён). Изменение = новая версия.
- Перед включением — прогон на синтетическом портфеле: доля одобрений, средний лимит, доля контрпредложений, ручных и отказов; отчёт в CI.
- Champion/challenger: детерминированное разбиение по хэшу ИНН, обе версии считаются, применяется одна [P15]. Could.

## 13. Тесты движка
- **Табличные тесты правил:** вход → ожидаемый вывод, по строке на правило и граничный случай (24,99% / 25% активов).
- **Golden-файлы по сценариям:** S1–S9, R1–R13, N1–N17 → ожидаемые исход, причины, флаги.
- **Свойства:** рост оборотов не уменьшает лимит; добавление поручителя не ухудшает исход; у каждого отказа есть причина; simulate и commit на одинаковых фактах совпадают.
- **Объяснимость:** у каждого сработавшего правила есть `explain` и `norm`.
