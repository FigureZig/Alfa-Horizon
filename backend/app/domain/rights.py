"""Права человека в компании — из сущностей реестров и ДБО, а не из настроек (docs/05 §2–3).

Чистые функции: факты компании (features.company_facts) + ИНН человека → роли, права и почему, с нормой.
"""

LEVELS = {"view": 1, "prepare": 2, "owner": 3}          # уровни доступа в ДБО по договору с банком
NORMS = {
    "self": "ГК РФ ст. 23 п. 1, ст. 24",
    "eio": "14-ФЗ ст. 40 п. 3 пп. 1; ГК РФ ст. 53 п. 1",
    "joint": "ГК РФ ст. 53 п. 1; ЕГРЮЛ СвПолном@ВидПолном = 1",
    "disqualified": "КоАП РФ ст. 3.11 ч. 1",
    "unreliable": "129-ФЗ ст. 7.1 п. 7 пп. «з.1»",
    "participant": "14-ФЗ ст. 46 п. 3",
    "bank_access": "договор ДБО",
    "poa": "ГК РФ ст. 185, 185.1 п. 4; 63-ФЗ ст. 17.2 ч. 1 п. 2",
}
POA_POWER = "CREDIT_AGREEMENT_SIGN"                    # полномочие «подписание кредитного договора» в МЧД
POA_STATUS = {"ACTIVE": "действует", "EXPIRED": "истекла", "REVOKED": "отозвана", "SUSPENDED": "приостановлена"}


def _poa_sign(poa: dict | None, facts: dict) -> tuple[bool, str | None]:
    """Подписывает ли представитель по МЧД кредитный договор, и если нет — почему."""
    if poa is None:
        return False, None
    if not poa["active"]:
        return False, f"МЧД {POA_STATUS.get(poa['status'], poa['status'].lower())} — подписывать по ней нельзя"
    if POA_POWER not in poa["powers"]:
        return False, "в МЧД нет полномочия на подписание кредитного договора"
    if facts.get("eio_mode") == "joint":
        return False, "руководители действуют совместно — доверенность нужна от всех"
    return True, None


def _eio_block(person: dict) -> str | None:
    if person.get("disqualified"):
        return "disqualified"
    if person.get("unreliable"):
        return "unreliable"
    return None


def rights(person_inn: str, facts: dict) -> dict:
    """Роли человека в компании и что ему можно: view, prepare (подготовить и подать), sign, approve (голос за крупную сделку)."""
    segment, roles, why = facts.get("segment"), [], []
    owner = segment == "IP" and facts.get("inn") == person_inn
    eio = None if segment == "IP" else next((e for e in facts.get("eio", []) if e["inn"] == person_inn), None)
    share = next((p["share"] for p in facts.get("participants", []) if p["inn"] == person_inn), None)
    level = next((a["level"] for a in facts.get("bank_access", []) if a["inn"] == person_inn), None)
    block = _eio_block(eio) if eio else None
    mode = "joint" if facts.get("eio_mode") == "joint" else "independent"
    poa = None if segment == "IP" else next((p for p in facts.get("poa", []) if p["representative_inn"] == person_inn), None)
    poa_sign, poa_why = _poa_sign(poa, facts)

    if owner:
        roles.append({"role": "owner"})
        why.append({"right": "sign", "allowed": True, "because": "предприниматель действует сам", "norm": NORMS["self"]})
    if eio:
        roles.append({"role": "eio", "title": eio["title"], "mode": mode, "blocked": block})
        if block:
            why.append({"right": "sign", "allowed": False, "norm": NORMS[block],
                        "because": "руководитель дисквалифицирован" if block == "disqualified"
                        else "сведения о руководителе в ЕГРЮЛ недостоверны"})
        else:
            why.append({"right": "sign", "allowed": True, "norm": NORMS[mode if mode == "joint" else "eio"],
                        "because": "руководитель действует без доверенности" if mode == "independent"
                        else "руководители действуют совместно: подписывают все"})
    if share is not None:
        roles.append({"role": "participant", "share": share})
        if segment == "LLC":
            why.append({"right": "approve", "allowed": True, "because": f"участник с долей {share:g}%",
                        "norm": NORMS["participant"]})
    if poa:
        roles.append({"role": "poa", "status": poa["status"], "valid_to": poa["valid_to"], "guid": poa["guid"]})
        why.append({"right": "sign", "allowed": poa_sign, "norm": NORMS["poa"],
                    "because": f"подписывает по МЧД до {'.'.join(reversed(poa['valid_to'].split('-')))}" if poa_sign
                    else poa_why})
    if level:
        roles.append({"role": "bank_access", "level": level})
        why.append({"right": "prepare", "allowed": LEVELS.get(level, 0) >= LEVELS["prepare"],
                    "because": f"доступ в ДБО: {level}", "norm": NORMS["bank_access"]})

    can = {   # счёт и кабинет компании видит тот, кому компания дала доступ: руководитель, ИП, пользователь ДБО, представитель
        "view": owner or eio is not None or level is not None or poa is not None,   # участник — только своё голосование
        "prepare": owner or (eio is not None and not block) or LEVELS.get(level, 0) >= LEVELS["prepare"],
        "sign": owner or (eio is not None and not block) or poa_sign,
        "approve": share is not None and segment == "LLC",
    }
    sign_mode = "self" if owner else mode if (eio is not None and not block) else "poa" if poa_sign else None
    return {"roles": roles, "can": can, "sign_mode": sign_mode, "why": why}


def signers(facts: dict) -> dict:
    """Кто должен подписать кредитный договор: ИП — сам; ЕИО независимо — любой из них или представитель по действующей
    МЧД; совместно — все (docs/05 §2)."""
    if facts.get("segment") == "IP":
        return {"mode": "self", "required": [facts["inn"]], "any_of": []}
    valid = [e["inn"] for e in facts.get("eio", []) if not _eio_block(e)]
    if facts.get("eio_mode") == "joint":
        return {"mode": "joint", "required": valid, "any_of": []}
    by_poa = [p["representative_inn"] for p in facts.get("poa", []) if _poa_sign(p, facts)[0]]
    return {"mode": "independent", "required": [], "any_of": valid + [inn for inn in by_poa if inn not in valid]}


def signed_enough(facts: dict, signed: set[str]) -> bool:
    need = signers(facts)
    if need["mode"] == "independent":
        return bool(set(need["any_of"]) & signed)
    return bool(need["required"]) and set(need["required"]) <= signed
