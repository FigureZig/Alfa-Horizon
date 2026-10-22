"""Каталог и цена: какие продукты доступны отрасли, из чего складывается ставка, сколько можно дать (docs/13)."""

from decimal import Decimal

from .calc import dec, floor_to, max_principal, round_to
from .okved import okved_class


def term_bucket(term_months: int, params: dict) -> str:
    return "short" if term_months <= params["short_term_max_months"] else "long"


def industry_spread(market: dict, section: str | None, bucket: str) -> Decimal:
    """Ставка раздела ОКВЭД минус средняя по МСП за тот же месяц (табл. 11 и 5 бюллетеня ЦБ), не ниже пола."""
    rates = market["by_section"].get(section) or market["other"]
    cfg = market["industry_spread"]
    raw = dec(rates[bucket]) - dec(market["msp_average"][bucket])
    return max(dec(cfg["floor"]), round_to(raw, cfg["rounding"]))


def risk_spread(pricing: dict, risk_class: str, security: str) -> Decimal:
    """Ожидаемые потери PD × LGD плюс операционные расходы и маржа, с округлением (docs/12 §5)."""
    expected_loss = dec(pricing["pd_for_price"][risk_class]) * dec(pricing["lgd"][security]) * 100
    return round_to(expected_loss + dec(pricing["opex_margin_pp"]), pricing["rounding_pp"])


def rate(pol: dict, section: str | None, term_months: int, risk_class: str, security: str) -> dict:
    bucket = term_bucket(term_months, pol["params"])
    key = dec(pol["market"]["key_rate"]["value"])
    industry = industry_spread(pol["market"], section, bucket)
    risk = risk_spread(pol["risk_pricing"], risk_class, security)
    return {"total": key + industry + risk, "key_rate": key, "industry": industry, "risk": risk,
            "section": section, "bucket": bucket, "risk_class": risk_class, "security": security}


def section_check(pol: dict, okved: str | None, section: str | None) -> tuple[bool, str | None]:
    """Кредитуем ли отрасль вообще: стоп по классу ОКВЭД или по разделу."""
    cls = okved_class(okved)
    if cls in pol["stop_codes"]:
        return False, pol["stop_codes"][cls]
    sec = pol["sections"].get(section)
    if sec is None:
        return False, "вид деятельности не определён"
    if sec.get("stop"):
        return False, sec["stop"]
    return True, None


def available_products(pol: dict, section: str | None, segment: str | None) -> list[str]:
    sec = pol["sections"].get(section) or {}
    return [code for code in sec.get("products", []) if segment in pol["products"][code]["segments"]]


def security_for(product: dict, segment: str) -> str:
    sec = product["security"]
    return sec.get(segment, sec["default"])


def contract_cap(contracts: list[dict] | None, product: dict) -> Decimal | None:
    if not contracts:
        return None
    best = max(dec(c["price"]) * (1 - dec(c.get("advancePercent", 0)) / 100) for c in contracts)
    return best * dec(product["contract_share"])


def caps(product: dict, facts: dict, term_months: int, rate_total: Decimal, pol: dict, collateral_value=None) -> list[dict]:
    """Все ограничения суммы; value=None — данных нет, движок спросит (docs/04 §3, COLLECT MIN)."""
    p = pol["params"]
    inflow = facts.get("inflow_avg")
    available = None if inflow is None else dec(p["p_payment"]) * dec(inflow) - dec(facts.get("debt_payments") or 0)
    out = []
    for code in product["caps"]:
        if code == "PRODUCT_MAX":
            value = dec(product["amount"]["max"])
        elif code == "TURNOVER":
            value = None if inflow is None else dec(p["k_overdraft"]) * dec(inflow)
        elif code == "PAYMENT_CAPACITY":
            value = None if available is None else max_principal(max(available, Decimal(0)), rate_total, term_months)
        elif code == "INTEREST_CAPACITY":
            value = None if available is None else max(available, Decimal(0)) * 1200 / dec(rate_total)
        elif code == "COLLATERAL":
            value = None if collateral_value is None else dec(collateral_value) * dec(product["ltv_max"])
        elif code == "CONTRACT":
            value = contract_cap(facts.get("contracts"), product)
        elif code == "SEASONAL_INFLOWS":
            value = None if inflow is None else dec(product["seasonal_share"]) * dec(inflow) * 12
        else:
            raise ValueError(f"неизвестный кап {code}")
        out.append({"code": f"CAP_{code}", "value": value})
    return out


def limit(product: dict, cap_list: list[dict], risk_class: str, params: dict) -> tuple[Decimal | None, str | None]:
    """Лимит = минимум известных капов × множитель класса, вниз до красивой суммы (docs/12 §5)."""
    known = [c for c in cap_list if c["value"] is not None]
    if not known:
        return None, None
    binding = min(known, key=lambda c: c["value"])
    raw = binding["value"] * dec(product["class_multiplier"][risk_class])
    step = params["amount_step_small"] if raw < 1_000_000 else params["amount_step_large"]
    return floor_to(raw, step), binding["code"]
