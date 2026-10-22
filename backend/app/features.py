"""Анти-коррупционный слой: ответы реестров и банка (форматы docs/09) → плоские факты движка (docs/04 §2).

На вход — payload снапшотов по источникам (None, если источник не ответил или данных нет), на выход — факты.
Форматы внешних систем дальше этого файла не протекают.
"""

from datetime import date
from decimal import Decimal
from statistics import fmean, pstdev

from .domain.calc import dec
from .domain.okved import section_of

OPF = {"12300": "LLC", "12267": "JSC", "12247": "JSC", "12200": "JSC"}   # ОКОПФ: ООО, непубличное АО, ПАО, АО
LIQUIDATION_STATUS = {"101"}                                              # ЕГРЮЛ СвСтатус@КодСтатусЮЛ: в стадии ликвидации
INFLOW_SKIP = {"loan", "own_transfer", "deposit"}                         # не выручка: кредиты, свои переводы, депозит


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month - (1 if end.day < start.day else 0)


def month_keys(today: date, n: int = 12) -> list[str]:
    """Последние n полных месяцев до текущего, от старого к новому."""
    y, m, keys = today.year, today.month, []
    for _ in range(n):
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
        keys.append(f"{y:04d}-{m:02d}")
    return keys[::-1]


def _fio(node: dict) -> str:
    return " ".join(filter(None, (node.get("@Фамилия"), node.get("@Имя"), node.get("@Отчество"))))


def _registry(f: dict, egrul: dict | None, egrip: dict | None) -> None:
    if egrul:
        ul = egrul["СвЮЛ"]
        status = ul.get("СвСтатус") or {}
        f.update(
            segment=OPF.get(ul.get("@КодОПФ"), "LLC"),
            name=ul["СвНаимЮЛ"]["@НаимЮЛПолн"],
            ogrn=ul["@ОГРН"],
            registered=ul["@ДатаОГРН"],
            okved=ul["СвОКВЭД"]["СвОКВЭДОсн"]["@КодОКВЭД"],
            okved_name=ul["СвОКВЭД"]["СвОКВЭДОсн"].get("@НаимОКВЭД"),
            liquidation=status.get("@КодСтатусЮЛ") in LIQUIDATION_STATUS,
            eio_mode="joint" if (ul.get("СвПолном") or {}).get("@ВидПолном") == "1" else "independent",
            eio=[{"inn": p["СвФЛ"]["@ИННФЛ"], "fio": _fio(p["СвФЛ"]), "title": p["СвДолжн"]["@НаимДолжн"],
                  "unreliable": bool(p.get("СвНедДанДолжнФЛ")), "disqualified": bool(p.get("СвДискв"))}
                 for p in ul.get("СведДолжнФЛ", [])],
            participants=[{"inn": u["СвФЛ"].get("@ИННФЛ"), "fio": _fio(u["СвФЛ"]),
                           "share": float(u["ДоляУстКап"]["РазмерДоли"]["Процент"])}
                          for u in (ul.get("СвУчредит") or {}).get("УчрФЛ", [])],
        )
    elif egrip:
        ip = egrip["СвИП"]
        fio = _fio(ip["СвФЛ"]["ФИОРус"])
        f.update(segment="IP", name=f"ИП {fio}", ogrn=ip["@ОГРНИП"], registered=ip["@ДатаОГРНИП"],
                 okved=ip["СвОКВЭД"]["СвОКВЭДОсн"]["@КодОКВЭД"], okved_name=ip["СвОКВЭД"]["СвОКВЭДОсн"].get("@НаимОКВЭД"),
                 liquidation=False, eio_mode="independent",
                 eio=[{"inn": ip["@ИННФЛ"], "fio": fio, "title": "Индивидуальный предприниматель"}], participants=[])


def _tax(f: dict, snaps: dict) -> None:
    if rsmp := snaps.get("rsmp"):
        f["msp_category"] = int(rsmp["Документ"]["@КатСубМСП"])
    if sshr := snaps.get("sshr"):
        f["headcount"] = int(sshr["Документ"]["СведССЧР"]["@КолРаб"])
    if snr := snaps.get("snr"):
        flags = snr["Документ"]["СведСНР"]
        f["tax_regime"] = next((r for r, key in (("USN", "@ПризнУСН"), ("ESHN", "@ПризнЕСХН"), ("AUSN", "@ПризнАУСН"))
                                if flags.get(key) == "1"), "OSN")
    if debtam := snaps.get("debtam"):
        f["tax_debt"] = sum((dec(x["@ОбщСумНедоим"]) for x in debtam["Документ"].get("СведНедоим", [])), Decimal(0))


def _financials(f: dict, girbo: list | None) -> None:
    if not girbo:
        return
    last = max(girbo, key=lambda r: r["period"])["typeCorrections"][0]["correction"]
    thousand = Decimal(1000)                                   # ГИР БО — тыс. ₽
    f.update(fin_period=max(r["period"] for r in girbo),
             assets=dec(last["balance"]["current1600"]) * thousand,
             revenue=dec(last["financialResult"]["current2110"]) * thousand,
             net_profit=dec(last["financialResult"]["current2400"]) * thousand)


def _turnover(f: dict, tx: dict | None, today: date) -> None:
    if not tx:
        return
    keys = month_keys(today)
    sums = dict.fromkeys(keys, Decimal(0))
    for item in tx["items"]:
        month = item["bookingDate"][:7]
        if item["direction"] == "in" and item.get("category") not in INFLOW_SKIP and month in sums:
            sums[month] += dec(item["amount"])
    series = [sums[k] for k in keys]
    f["inflows_monthly"] = series
    f["turnover_months"] = sum(1 for s in series if s > 0)
    f["balance"] = dec(tx["balance"]["amount"]) if tx.get("balance") else None
    if f["turnover_months"] == 0:
        return
    values = [float(s) for s in series]
    mean = fmean(values)
    f["inflow_avg"] = (sum(series, Decimal(0)) / len(series)).quantize(Decimal("0.01"))
    f["inflow_cv"] = round(pstdev(values) / mean, 4) if mean else None
    prev, last3 = fmean(values[:9]), fmean(values[9:])
    f["inflow_trend"] = round(last3 / prev - 1, 4) if prev else None


def _bki(f: dict, bki: dict | None, info: dict | None) -> None:
    """Полный отчёт — только с согласием; информационная часть (обращения, отказы) — без него."""
    f["bki_known"] = bki is not None
    f["bki_info_known"] = bki is not None or info is not None
    if info is not None:
        f["bki_requests_30d"] = int(info["requests"]["last30days"])
    if bki is None:
        return
    report = bki.get("CreditReportOfLegalPerson") or bki.get("CreditReportOfNaturalPerson")
    credits = (report.get("Credits") or {}).get("Credit", [])
    active = [c for c in credits if dec(c.get("PrincipalDebt", 0)) > 0]
    f.update(
        active_credits=len(active),
        debt_payments=sum((dec(c.get("AvgMonthPaymentSum", 0)) for c in active), Decimal(0)),
        max_overdue_days=max((int(c.get("PastDepthOfDelayInDay", 0)) for c in credits), default=0),
        two_payments_skipped=any(c.get("TwoPaymentsSkipped") for c in credits),
        bki_requests_30d=int((report.get("RequestsStatistic") or {}).get("NumberOfRequests", 0)),
        bankruptcy=bool((report.get("Subject") or {}).get("Bankruptcy")) or f.get("bankruptcy", False),
    )


def account_operations(tx: dict | None) -> list[dict]:
    """Выписка → операции со знаком: приход +, расход −."""
    return [{"date": date.fromisoformat(t["bookingDate"]), "amount": dec(t["amount"]) * (1 if t["direction"] == "in" else -1),
             "purpose": t["purpose"], "category": t.get("category")} for t in (tx or {}).get("items", [])]


def cash_flow(tx: dict | None, today: date, months: int = 6) -> dict | None:
    """Выписка → остаток, обороты по месяцам (приход без кредитов и своих переводов), текущий месяц, последние операции."""
    if not tx:
        return None
    keys, current = month_keys(today, months), f"{today.year:04d}-{today.month:02d}"
    sums = {k: {"income": Decimal(0), "expenses": Decimal(0)} for k in [*keys, current]}
    for item in tx["items"]:
        month = item["bookingDate"][:7]
        if month not in sums:
            continue
        if item["direction"] == "out":
            sums[month]["expenses"] += dec(item["amount"])
        elif item.get("category") not in INFLOW_SKIP:
            sums[month]["income"] += dec(item["amount"])
    latest = sorted(enumerate(tx["items"]), key=lambda x: (x[1]["bookingDate"], x[0]), reverse=True)[:10]
    return {
        "balance": dec(tx["balance"]["amount"]) if tx.get("balance") else None,
        "as_of": (tx.get("balance") or {}).get("asOf"),
        "months": [{"month": k, **sums[k]} for k in keys],
        "current": {"month": current, **sums[current]},
        "recent": [{"id": f"{t['bookingDate']}:{i}", "date": t["bookingDate"], "title": t["purpose"],
                    "amount": dec(t["amount"]) * (-1 if t["direction"] == "out" else 1), "direction": t["direction"],
                    "category": t.get("category"), "counterparty_inn": t.get("counterpartyInn")} for i, t in latest],
    }


def person_links(card: dict | None) -> list[dict]:
    """Карточка клиента в банке → компании, к которым у человека доступ в ДБО."""
    return [{"inn": c["companyInn"], "level": c["level"]} for c in (card or {}).get("companies", [])]


def company_facts(inn: str, snaps: dict, today: date) -> dict:
    """snaps: {источник: payload | None}. Возвращает факты; неизвестное остаётся None или отсутствует."""
    f: dict = {"inn": inn, "segment": None, "eio": [], "participants": [], "conflicts": []}
    _registry(f, snaps.get("egrul"), snaps.get("egrip"))
    if f.get("okved"):
        f["section"] = section_of(f["okved"])
    if f.get("registered"):
        f["age_months"] = months_between(date.fromisoformat(f["registered"]), today)
    _tax(f, snaps)
    _financials(f, snaps.get("girbo"))
    _turnover(f, snaps.get("bank_tx"), today)
    if legal := snaps.get("legal"):
        f["bankruptcy"] = bool((legal.get("bankruptcy") or {}).get("stage"))
    _bki(f, snaps.get("bki"), snaps.get("bki_info"))

    if f.get("inflow_avg") and f.get("debt_payments") is not None:
        f["debt_load"] = round(float(f["debt_payments"] / f["inflow_avg"]), 4)
    if f.get("revenue") and f.get("inflows_monthly"):
        f["bank_share"] = round(min(1.0, float(sum(f["inflows_monthly"]) / f["revenue"])), 4)

    if access := snaps.get("bank_access"):
        f["bank_access"] = [{"inn": p["personInn"], "fio": p["fio"], "level": p["level"]} for p in access["persons"]]
        kyc_director = access.get("kycDirectorInn")
        if kyc_director and f["eio"] and kyc_director not in {e["inn"] for e in f["eio"]}:
            f["conflicts"].append("руководитель в ЕГРЮЛ и в анкете банка разный")
    if charter := snaps.get("bank_charter"):
        f["charter"] = {"decisionMethod": charter.get("decisionMethod"), "limits": charter.get("limits", [])}
    if eis := snaps.get("eis"):
        f["contracts"] = [c for c in eis.get("contracts", []) if c["endDate"] >= today.isoformat()]
    if mchd := snaps.get("mchd"):                     # доверенности компании: кто и что вправе подписывать
        f["poa"] = [{"guid": p["guid"], "representative_inn": p["representative"]["inn"], "fio": p["representative"]["fio"],
                     "status": p["status"], "powers": [x["code"] for x in p["powers"]], "valid_to": p["validTo"],
                     "active": p["status"] == "ACTIVE" and p["validFrom"] <= today.isoformat() <= p["validTo"]}
                    for p in mchd.get("items", [])]
    return f
