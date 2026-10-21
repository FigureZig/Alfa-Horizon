"""«Своя персона» из осей и pairwise-наборы: каждая пара значений любых двух осей встречается хотя бы в одном векторе.

Генерация — IPOG (allpairspy). Вектор → описание (seed.world.custom) → ответы источников в том виде, как их отдаст
WireMock, минус упавшие источники → факты → решение движка. Наборов три:
  HEALTHY — все источники отвечают: на этих парах проверяются числа оферт;
  FAULTY  — упал источник или режим предодобрения: проверяется, что неизвестное не превращается в «да» или «нет»;
  стоп-факторы — полный перебор (их мало), чтобы не забивать отказами пары «продукт × сумма».
"""

from datetime import date

from allpairspy import AllPairs

from app.domain import engine
from app.features import company_facts
from seed import world

FORMS = {"IP": ("IP", 1), "LLC_SOLE": ("LLC", 1), "LLC_MULTI": ("LLC", 3), "JSC": ("JSC", 2)}   # вид, сколько людей
OKVED = {
    "I": ["56.10", "Деятельность ресторанов и услуги по доставке продуктов питания"],
    "G": ["46.90", "Торговля оптовая неспециализированная"],
    "C": ["10.71", "Производство хлеба и мучных кондитерских изделий, тортов и пирожных недлительного хранения"],
    "F": ["41.20", "Строительство жилых и нежилых зданий"],
    "A": ["01.11", "Выращивание зерновых (кроме риса), зернобобовых культур и семян масличных культур"],
    "J": ["62.01", "Разработка компьютерного программного обеспечения"],
    "H": ["49.41", "Деятельность автомобильного грузового транспорта"],
    "Q": ["86.21", "Общая врачебная практика"],
}
PROFILES = {   # профиль → класс риска по карте docs/12 (ИП / ООО): strong A/A, average B/B, weak C/C, risky D/D
    "strong": {"age_months": 84, "headcount": 40, "inflow_avg": 8_000_000, "inflow_cv": 0.1, "inflow_trend": 0.1,
               "debt_load": 0.05, "bki_requests": 0, "profit_margin": 0.08},
    "average": {"age_months": 40, "headcount": 15, "inflow_avg": 3_000_000, "inflow_cv": 0.35, "inflow_trend": -0.15,
                "debt_load": 0.25, "overdue_days": 3, "bki_requests": 3, "profit_margin": 0.04},
    "weak": {"age_months": 20, "headcount": 8, "inflow_avg": 1_500_000, "inflow_cv": 0.5, "inflow_trend": -0.15,
             "debt_load": 0.35, "overdue_days": 3, "bki_requests": 3, "profit_margin": 0.01},
    "risky": {"age_months": 9, "headcount": 4, "inflow_avg": 800_000, "inflow_cv": 0.6, "inflow_trend": -0.3,
              "debt_load": 0.35, "overdue_days": 15, "bki_requests": 6, "profit_margin": -0.03},
}
REQUEST = {   # продукт → цель, срок, «посильная» сумма в долях средних поступлений
    "OVERDRAFT": ("cash_gap", 12, 0.25), "EXPRESS": ("cash_gap", 24, 0.6), "WORKING_CAPITAL": ("stock", 24, 0.8),
    "INVESTMENT": ("equipment", 60, 1.5), "CONTRACT": ("contract", 12, 0.8), "AGRO_SEASONAL": ("stock", 10, 1.0),
}
AMOUNTS = ("below_min", "at_min", "fits", "large", "above_authority")
TERMS = ("min", "mid", "max")
FAULTS = {"none": (), "bki_down": ("bki", "bki_info"), "registry_down": ("egrul", "egrip"), "tx_down": ("bank_tx",)}
HEALTHY = {"form": list(FORMS), "section": list(OKVED), "product": list(REQUEST), "amount": list(AMOUNTS),
           "profile": list(PROFILES), "term": list(TERMS)}
FAULTY = {"form": list(FORMS), "section": ["G", "A", "J"], "product": list(REQUEST), "amount": ["fits", "large"],
          "profile": list(PROFILES), "fault": ["bki_down", "registry_down", "tx_down"], "mode": ["commit", "simulate"]}

# Стоп-фактор → правка описания, код причины, вид отказа, источники, из которых он виден
STOPS = {
    "tax_debt": ({"tax_debt": 120_000}, "STOP_TAX_DEBT", "STOP_FIXABLE", ("debtam",)),
    "overdue_90": ({"overdue_days": 120}, "STOP_DELINQUENCY", "STOP_FINAL", ("bki",)),
    "bankruptcy": ({"flags": ["bankruptcy"]}, "STOP_BANKRUPTCY", "STOP_FINAL", ("legal", "bki")),
    "liquidation": ({"flags": ["liquidation"]}, "STOP_LIQUIDATION", "STOP_FINAL", ("egrul",)),
    "unreliable_eio": ({"flags": ["unreliable_eio"]}, "STOP_EIO_UNRELIABLE", "STOP_FIXABLE", ("egrul",)),
    "disqualified_eio": ({"flags": ["disqualified_eio"]}, "STOP_EIO_DISQUALIFIED", "STOP_FIXABLE", ("egrul",)),
    "industry_K": ({"okved": ["64.19", "Денежное посредничество прочее"]}, "POL_INDUSTRY", "POLICY", ("egrul", "egrip")),
    "gambling_92": ({"okved": ["92.1", "Деятельность по организации и проведению азартных игр и заключению пари"]},
                    "POL_INDUSTRY", "POLICY", ("egrul", "egrip")),
}
STOP_FAULTS = ("none", "registry_down", "bki_down")


def vectors(axes: dict = HEALTHY) -> list[dict]:
    names = list(axes)
    return [dict(zip(names, row, strict=True)) for row in AllPairs(list(axes.values()))]


def stop_vectors() -> list[dict]:
    """Полный перебор: стоп × форма × сбой, остальное — средняя компания с посильным экспресс-кредитом."""
    out = []
    for stop, (patch, *_) in STOPS.items():
        for form in FORMS:
            if form == "IP" and set(patch.get("flags", [])) & world.UL_ONLY_FLAGS:
                continue                                   # у ИП нет отметок ЕГРЮЛ — такой персоны не бывает
            out += [{"stop": stop, "form": form, "fault": fault, "section": "G", "product": "EXPRESS", "amount": "fits",
                     "profile": "average", "mode": "commit"} for fault in STOP_FAULTS]
    return out


def amount_for(level: str, product: str, inflow_avg: int, pol: dict) -> int:
    lo, hi = pol["products"][product]["amount"]["min"], pol["products"][product]["amount"]["max"]
    match level:
        case "below_min":
            return lo // 2
        case "at_min":
            return lo
        case "fits":
            return min(hi, max(lo, round(REQUEST[product][2] * inflow_avg, -4)))
        case "large":                                      # ≈ 33% активов персоны → крупная сделка для ООО и АО
            return min(hi, max(lo, round(2.4 * inflow_avg, -5)))
        case "above_authority":
            return pol["params"]["auto_authority_max"] + 2_000_000
    raise ValueError(level)


def term_for(level: str, product: str, pol: dict) -> int:
    bounds = pol["products"][product]["term_months"]
    return {"min": bounds["min"], "mid": REQUEST[product][1], "max": bounds["max"]}[level]


def build(v: dict, number: int, pol: dict, today: date) -> dict:
    """Персона, запрос и решение по вектору. number делает ИНН и ОГРН персоны уникальными.
    Чего нет в векторе: срок — типовой, источники — все, режим — решение по заявке (commit)."""
    v = {"term": "mid", "fault": "none", "mode": "commit", **v}
    kind, people_count = FORMS[v["form"]]
    spec = {"kind": kind, "participants": people_count, "okved": OKVED[v["section"]], **PROFILES[v["profile"]]}
    if "stop" in v:
        spec.update(STOPS[v["stop"]][0])
    amount = amount_for(v["amount"], v["product"], spec["inflow_avg"], pol)
    request = {"product": v["product"], "amount": amount, "term_months": term_for(v["term"], v["product"], pol),
               "goal": REQUEST[v["product"]][0]}
    if v["product"] == "CONTRACT":
        spec["contract_price"] = 3 * max(amount, pol["products"]["CONTRACT"]["amount"]["min"])
    if v["product"] == "INVESTMENT":
        request["collateral_value"] = round(amount * 1.6)

    company, people = world.custom(spec, number, today)
    errors = world.validate(company, people, today)
    if errors:
        raise ValueError(f"персона {v} некорректна: {errors}")
    served = {s: body for s, body in world.served(company, people, today).items() if s not in FAULTS[v["fault"]]}
    facts = company_facts(company["inn"], served, today)
    return {"vector": v, "spec": spec, "company": company, "people": people, "sources": sorted(served),
            "request": request, "facts": facts, "decision": engine.decide(facts, request, pol, v["mode"])}
