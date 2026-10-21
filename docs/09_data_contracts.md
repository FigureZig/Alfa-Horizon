# 09. Контракты данных и ручки внешних систем

Ground truth по внешним контрактам (21.10.2026). Визуализация — `diagrams/c4-data-flows.drawio` (L2 — ручки и поля, L3-W — интеграции и устойчивость)
и `diagrams/scenarios-bpmn.drawio` (на схемах сценариев видно, на каком шаге какие данные приходят). Внутренний API и события — `06_architecture.md` §5–6.
Скоринг и рейтинг — **отдельная проработка**, здесь только сырые поля, которые им понадобятся (§7).

---

## 1. Принципы
1. **Имена полей моков = имена в реальных спецификациях.** ЕГРЮЛ — формат ФНС 4.06 (приложение 1 к приказу ЕД-7-14/820@, `refs/data_sources/fns_egrul_format_4.06_*`).
   Открытые данные ФНС — XSD наборов (`refs/data_sources/fns_opendata_*.xsd`). ГИР БО — JSON сайта bo.nalog.gov.ru (`girbo_bfo_example_structure.json`).
   БКИ — формат ЦБ «Кредитный отчёт» v3.4 (`refs/cbr/cbr_credit_report_format_v3.4_*.txt`). Реестр МЧД — статусы публичного сервиса m4d.nalog.gov.ru.
   Замена мока на реальную интеграцию = смена адаптера, а не модели данных.
2. **Наружу ходит только Worker** (модуль `integrations`): таймауты, ретраи с backoff, кэш с TTL. Ответ сохраняется **снапшотом** в PostgreSQL
   (ИНН, источник, дата получения, payload). API читает только снапшоты, поэтому экран не падает, если реестр недоступен.
3. **Формат моков — JSON**, даже там, где оригинал XML (ЕГРЮЛ, БКИ): ключи повторяют имена элементов и атрибутов XML. **[упрощение]**
   Один стаб на ручку, тело выбирается по ИНН из `__files/<источник>/<ИНН>.json` шаблоном WireMock; тела генерирует скрипт из пресетов (06 §12).
4. **Сбои реестров воспроизводимы на лету:** стабы отказов с приоритетом 1, задержки, Scenarios WireMock — без перезапуска (`07_resilience.md` §7).
5. **Песочница** меняет «реестры» через WireMock admin API → событие `registry.changed` → Worker обновляет снапшот → `parties` пересчитывает права.

---

## 2. Каталог внешних ручек (моки WireMock)

| Система | Ручка | Ключевые поля ответа (как в спецификации) | Основа | Кэш / TTL | → Сущности (05 §3, 04 §2) |
|---|---|---|---|---|---|
| **ЕГРЮЛ** | `GET /egrul/v1/legal-entities/{inn}` | `СвЮЛ@ИНН, @ОГРН, @КодОПФ, @ПолнНаимОПФ` · `СвНаимЮЛ@НаимЮЛПолн` · `СвСтатус@КодСтатусЮЛ, @НаимСтатусЮЛ` · `СвОКВЭД/СвОКВЭДОсн@КодОКВЭД, @НаимОКВЭД` · `СведДолжнФЛ[]`: `СвФЛ(@Фамилия, @Имя, @Отчество, @ИННФЛ)`, `СвДолжн(@ВидДолжн, @НаимДолжн)`, `СвНедДанДолжнФЛ(@ПризнНедДанДолжнФЛ, @ТекстНедДанДолжнФЛ)`, `СвДискв(@ДатаНачДискв, @ДатаРеш)` · `СвПолном@ВидПолном` (1 — совместно, 2 — независимо) · `СвУчредит`: `УчрФЛ[] / УчрЮЛРос[]` + `ДоляУстКап(@НоминСтоим, РазмерДоли@Процент)` | формат ФНС 4.06 ✅ | 24 ч + сброс по `registry.changed` | Company, ExecutiveAuthority (mode = ВидПолном), Participation, RegistryFlag, Disqualification |
| **ЕГРИП** | `GET /egrip/v1/entrepreneurs/{inn}` | ОГРНИП, ФИО, статус, ОКВЭД | формат ФНС 4.06 (ЕГРИП) 🟡 | 24 ч | Company(ИП), Person |
| **ФНС: реестр МСП** | `GET /fns/v1/rsmp/{inn}` | `ОргВклМСП / ИПВклМСП` · `@КатСубМСП` · `@ВидСубМСП` · `@ДатаВклМСП` · `@ССЧР` · `СвОКВЭД` | XSD `rsmp` ✅ | 30 дн. | Company.mspCategory |
| **ФНС: численность** | `GET /fns/v1/sshr/{inn}` | `СведССЧР@КолРаб` | XSD `sshr2019` ✅ | 30 дн. | TaxProfile.headcount |
| **ФНС: уплаченные налоги** | `GET /fns/v1/paytax/{inn}` | `СвУплСумНал[]@НаимНалог, @СумУплНал` | XSD `paytax` ✅ | 30 дн. | TaxProfile.paid |
| **ФНС: недоимки** | `GET /fns/v1/debtam/{inn}` | `СведНедоим[]@НаимНалог, @СумНедНалог, @СумПени, @СумШтраф, @ОбщСумНедоим` | XSD `debtam` ✅ | 7 дн. | TaxDebt (стоп-фактор / маркер «1764»: ≤ 50 тыс. ₽) |
| **ФНС: налоговые режимы** | `GET /fns/v1/snr/{inn}` | `СведСНР@ПризнУСН, @ПризнЕСХН, @ПризнАУСН, @ПризнСРП` | XSD `snr` ✅ | 30 дн. | TaxProfile.regime |
| **ФНС: реестр дисквалифицированных** | `GET /fns/v1/disqualified?inn=&fio=` | G1 дата рождения · G3 организация · G4 ИНН орг. · G5 должность · G6 статья КоАП · G10 срок · G11 дата начала | CSV-структура ФНС ✅ (данные от 04.10.2026) | 1 дн. | Disqualification |
| **ГИР БО** | `GET /girbo/v1/organizations/search?query={inn}` → `GET /girbo/v1/organizations/{id}/bfo` | `period`, `actualBfoDate`, `mspCategory`, `typeCorrections[0].correction.balance.current1600` (итог актива), `.current1300`, `.current1400`, `.current1500`, `financialResult.current2110` (выручка), `.current2400` (чистая прибыль); суммы в тыс. ₽ | живой JSON bo.nalog.gov.ru ✅ (не документирован) | 30 дн. | FinancialStatement → порог крупной сделки (L1) |
| **БКИ: кредитный отчёт** | `POST /bki/v1/credit-reports` (тело: субъект, ссылка на Consent, цель) | `CreditReportOfLegalPerson` / `CreditReportOfNaturalPerson`: `Subject(Identity, Bankruptcy[BRDate, BankruptcyStage, BRCase])` · `Credits/Credit[]`: `DateOfConclusion, Amount, CurrentLimit, PrincipalDebt, OverdueAmount, PastdueDate, PastDepthOfDelayInDay, AvgMonthPaymentSum, TwoPaymentsSkipped, LastPaymentDate` · `OtherJudgements/Judgement(CaseNumber, Decision)` · `RequestsStatistic/NumberOfRequests` | формат ЦБ v3.4 ✅ | на заявку | CreditHistory (**только при действующем Consent**, 218-ФЗ ст. 6 ч. 9) |
| **БКИ: информационная часть** | `POST /bki/v1/info-part` | наличие обращений и отказов | 218-ФЗ ст. 6 ч. 9.1 ✅ (без согласия) | 1 дн. | предодобрение (K1) |
| **Реестр МЧД** | `GET /mchd/v1/poa/{guid}` · `GET /mchd/v1/poa?principalInn=&representativeSnils=` | `guid`, `status` (ACTIVE / EXPIRED / REVOKED / SUSPENDED), `principal(inn, ogrn)`, `representative(snils, inn, fio)`, `powers[](code, name)`, `validFrom`, `validTo` | статусы m4d 🟡; коды полномочий — Классификатор ЕСНСИ (в моке плейсхолдер `CREDIT_AGREEMENT_SIGN`) ⚠️ | 1 ч + перепроверка перед подписью | PowerOfAttorney |
| **Юр. проверки** | `GET /legal-checks/v1/{inn}` | `bankruptcy(stage, efrsbDate)`, `arbitration(asDefendantCount, claimsSum)`, `enforcement(count, sum)`, `sanctionsListHit` | сокращённый контракт **[упрощение]** | 1 дн. | RegistryFlag |
| **Банк: ядро** | `GET /bank-core/v1/persons/{id}` · `/companies/{inn}/access` · `/companies/{inn}/charter` · `/accounts/{inn}/transactions?from&to` | KYC-статус · доступы ДБО (`view` / `prepare`) · устав (`limits[]`, `decisionMethod: notary / protocol / tech_means`) · транзакции (`bookingDate, amount, direction, counterpartyInn, purpose, category`) | внутренний контракт банка **[наш дизайн]** | 1 ч | Person, BankAccess, CharterLimit, Turnover |
| **АБС** | `POST /abs/v1/loans` · `POST /abs/v1/loans/{id}/disburse` (заголовок `Idempotency-Key`) | `loanAccount`, `status` (OPENED / DISBURSED / FAILED), `schedule[]` | внутренний контракт **[наш дизайн]** | — | Loan |
| **ЕИС (K5)** | `GET /eis/v1/contracts?supplierInn=` | `regNum, customer, price, signDate, endDate, advancePercent, treasurySupport` | сокращённый контракт **[упрощение]** | 1 дн. | Signal TENDER_WON |
| **WireMock admin** (только демо) | `POST /__admin/mappings` · `POST /__admin/scenarios/reset` | — | WireMock | — | песочница |
| **LLM** (опционально) | `POST /v1/chat/completions` | OpenAI-compatible | — | — | не в пути решения |

### Пример: ответ мока ЕГРЮЛ (JSON-зеркало XML 4.06), сценарий R6 — два директора совместно
```json
{
  "СвЮЛ": {
    "@ОГРН": "1027700000001", "@ИНН": "7700000001", "@КодОПФ": "12300", "@ПолнНаимОПФ": "Общество с ограниченной ответственностью",
    "СвНаимЮЛ": { "@НаимЮЛПолн": "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ \"СЕВЕРНЫЙ ХЛЕБ\"" },
    "СвОКВЭД": { "СвОКВЭДОсн": { "@КодОКВЭД": "10.71", "@НаимОКВЭД": "Производство хлеба и мучных кондитерских изделий..." } },
    "СвПолном": { "@ВидПолном": "1" },
    "СведДолжнФЛ": [
      { "СвФЛ": { "@Фамилия": "Иванов", "@Имя": "Иван", "@Отчество": "Иванович", "@ИННФЛ": "770000000001" },
        "СвДолжн": { "@ВидДолжн": "02", "@НаимДолжн": "Генеральный директор" } },
      { "СвФЛ": { "@Фамилия": "Петрова", "@Имя": "Анна", "@Отчество": "Сергеевна", "@ИННФЛ": "770000000002" },
        "СвДолжн": { "@ВидДолжн": "02", "@НаимДолжн": "Генеральный директор" } }
    ],
    "СвУчредит": { "УчрФЛ": [
      { "СвФЛ": { "@Фамилия": "Иванов", "@Имя": "Иван", "@ИННФЛ": "770000000001" }, "ДоляУстКап": { "@НоминСтоим": "6000", "РазмерДоли": { "Процент": "60" } } },
      { "СвФЛ": { "@Фамилия": "Сидоров", "@Имя": "Пётр", "@ИННФЛ": "770000000003" }, "ДоляУстКап": { "@НоминСтоим": "4000", "РазмерДоли": { "Процент": "40" } } }
    ] }
  }
}
```
Синтетика, ИНН и ОГРН вымышленные. Контрольные суммы ИНН в генераторе будем считать по алгоритму ФНС, чтобы валидация на бэке была настоящей.

---

## 3. Карта данных: поле → сущность → правило → сценарии

| Поле источника | Сущность | Правило (05 §3) | Норма | Сценарии |
|---|---|---|---|---|
| ЕГРЮЛ `СведДолжнФЛ` | ExecutiveAuthority | `sign` у ЕИО | 14-ФЗ ст. 40 п. 3 | все |
| ЕГРЮЛ `СвПолном@ВидПолном` | ExecutiveAuthority.mode | совместная подпись — нужны все | ГК ст. 53 п. 1 | R6 |
| ЕГРЮЛ `СвНедДанДолжнФЛ@ПризнНедДанДолжнФЛ` | RegistryFlag | блок `sign` | 129-ФЗ ст. 7.1, 23 | R10 |
| ЕГРЮЛ `СвДискв` + реестр дисквалифицированных G4, G10, G11 | Disqualification | блок `sign` | КоАП ст. 3.11 | R10 |
| ЕГРЮЛ `СвУчредит / ДоляУстКап / Процент` | Participation | крупная сделка (участников > 1), поручительство, заинтересованность | 14-ФЗ ст. 45, 46; ГК ст. 361 | R2, R3, R7, R8, R9 |
| ЕГРЮЛ `@КодОПФ / @ПолнНаимОПФ` | Company.opf | ООО → 14-ФЗ, АО («ЗАО/ОАО») → 208-ФЗ, ИП → без корпоративных согласий | ГК ст. 66, 66.3 | R1, R13 |
| ЕГРЮЛ `СвОКВЭДОсн@КодОКВЭД` | Company.okved | подбор продукта, отраслевой спред ставки (табл. 11 ЦБ) | — (наш вывод, 05 §11) | все |
| ГИР БО `balance.current1600` | FinancialStatement.assets | `сумма ≥ 25% активов` → крупная сделка | 14-ФЗ ст. 46 п. 1; 208-ФЗ ст. 78 | R2, R3, R13 |
| ФНС `СведНедоим@ОбщСумНедоим` | TaxDebt | стоп-фактор (порог в политике) | наша политика; маркер 1764 (≤ 50 тыс. ₽, ⚠️) | все |
| ФНС `@КатСубМСП` | Company.mspCategory | доступность продуктов и госпрограмм | 209-ФЗ ст. 4 | все |
| Реестр МЧД `status, powers[], validTo` | PowerOfAttorney | `sign` у представителя; перепроверка перед подписью | ГК ст. 185.1; 63-ФЗ ст. 17.2 | R5 |
| Банк `access (view / prepare)` | BankAccess | `prepare`, inbox | договор ДБО | R4, R8 |
| Банк `charter.limits, decisionMethod` | CharterLimit | согласие по уставу; способ решения ОСУ | ГК ст. 174, 67.1 | R3, R11 |
| Банк `transactions` | Turnover | предодобрение, лимит овердрафта, радар разрыва (K1) | ГК ст. 850 (овердрафт) | R1, K1–K2 |
| БКИ `Credits / OverdueAmount, PastDepthOfDelayInDay`, `Bankruptcy` | CreditHistory | стоп-факторы; входы скоринга (§7) | 218-ФЗ | все (после Consent) |
| Заявка: согласие на БКИ | Consent | запрос в БКИ только при действующем согласии; 1 год | 218-ФЗ ст. 6 ч. 9–10 | все |
| ЕИС `contracts` | Signal | оффер под контракт (K5) | 44-ФЗ | K5 |

---

## 4. Внутренние события и API для фронта
Перенесены в `06_architecture.md` §5 (ручки) и §6 (события и задачи), чтобы не было двух версий.

---

## 5. Отказоустойчивость ручек
Таймауты, ретраи с jitter, breaker, bulkhead, политики фактов, критичные проверки только на свежих данных, идемпотентность АБС и инъекция отказов — `07_resilience.md`. TTL по источникам — таблица §2.

---

## 6. Скоринг и рейтинг — вне этого документа
Отдельная проработка (порт `decisioning.RiskModel`). Здесь только **сырые поля**, которые уже приходят через ручки выше и пригодятся как входы:
обороты и их стабильность (банк), `OverdueAmount` / `PastDepthOfDelayInDay` / `AvgMonthPaymentSum` / `NumberOfRequests` (БКИ), `current1600` / `current2110` / `current2400` (ГИР БО),
`ОбщСумНедоим` / `СумУплНал` (ФНС), возраст бизнеса (`ДатаОГРН`), ОКВЭД, категория МСП. Отбор признаков, веса и калибровка — не здесь.

## Источники
Спецификации: `refs/data_sources/fns_egrul_format_4.06_pril1_ED-7-14-820.docx` ([nalog.gov.ru](https://www.nalog.gov.ru/html/sites/www.new.nalog.ru/docs/about_fts/docs/pril1714820.docx)),
`refs/data_sources/fns_opendata_*.xsd` ([реестр МСП](https://www.nalog.gov.ru/opendata/7707329152-rsmp/)), [реестр дисквалифицированных лиц](https://www.nalog.gov.ru/opendata/7707329152-registerdisqualified/),
ГИР БО (bo.nalog.gov.ru, публичный JSON, проверен 21.10.2026), формат ЦБ «Кредитный отчёт» v3.4 ([pravo.ppt.ru](https://pravo.ppt.ru/pismo/bank/n--339425)),
МЧД ([ToolFox](https://toolfox.ru/blog/kak-proverit-mchd-na-saite-fns), [nalog-nalog.ru о классификаторе полномочий](https://nalog-nalog.ru/spravochnaya_informaciya/fns-rasskazala-o-kodah-polnomochij-dlya-mchd/)). Все нормы и цифры — в `10_sources.md`.
