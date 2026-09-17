"""Clasificacion de oportunidad de una Company, basada en reglas simples.

Es una senal interna calculada a partir de los datos encontrados (categoria,
nombre, descripcion) — no una afirmacion de que la empresa realmente
necesite el servicio. Trabaja sobre los campos normalizados de Company, no
sobre tags de una fuente en particular, para servir igual a Overpass que a
una futura fuente (Google Places, etc.).
"""

RULES = [
    {
        "category": "bodega",
        "keywords": ["bodega", "warehouse"],
        "points": 20,
        "reason": "cuenta con instalaciones de bodega",
    },
    {
        "category": "distribuidora",
        "keywords": ["distribuidora", "distribucion", "distribución"],
        "points": 20,
        "reason": "aparece como empresa de distribucion",
    },
    {
        "category": "alimentos",
        "keywords": ["alimentos", "alimenticia"],
        "points": 15,
        "reason": "pertenece al sector de alimentos",
    },
    {
        "category": "logistica",
        "keywords": ["logistica", "logística"],
        "points": 15,
        "reason": "pertenece al sector de logistica",
    },
    {
        "category": "mayorista",
        "keywords": ["mayorista", "mayoreo", "wholesale"],
        "points": 10,
        "reason": "es una empresa mayorista",
    },
    {
        "category": "importadora",
        "keywords": ["importadora", "importacion", "importación"],
        "points": 10,
        "reason": "es una empresa importadora",
    },
    {
        "category": "almacenamiento",
        "keywords": ["almacenamiento", "almacen", "almacén", "storage"],
        "points": 10,
        "reason": "cuenta con instalaciones de almacenamiento",
    },
]

# 80-100: alta | 50-79: media | 0-49: baja
OPPORTUNITY_THRESHOLDS = ((80, "alta"), (50, "media"))

LEVEL_TEXT = {"alta": "alta oportunidad", "media": "oportunidad media", "baja": "baja oportunidad"}


def score_company(company_data):
    """Recibe un dict con 'category', 'name', 'description' (los que ya
    produce cualquier data source) y devuelve (score, opportunity_level, reasons).
    """
    text = " ".join(
        filter(None, [company_data.get("name"), company_data.get("description")])
    ).lower()
    category = (company_data.get("category") or "").lower()

    score = 0
    reasons = []
    for rule in RULES:
        matches = category == rule["category"] or any(kw in text for kw in rule["keywords"])
        if matches:
            score += rule["points"]
            reasons.append(rule["reason"])

    score = min(score, 100)
    return score, _level_for_score(score), reasons


def _level_for_score(score):
    for threshold, level in OPPORTUNITY_THRESHOLDS:
        if score >= threshold:
            return level
    return "baja"


def build_reasons_summary(opportunity_level, reasons):
    """Frase legible para mostrar en la ficha de empresa."""
    label = LEVEL_TEXT.get(opportunity_level, opportunity_level)

    if not reasons:
        return (
            f"Clasificada como {label}: no se detectaron senales relevantes "
            "en los datos disponibles."
        )

    return f"Clasificada como {label} debido a que " + ", y ".join(reasons) + "."
