"""Genera un mensaje sugerido y personalizable para contactar a una empresa.

No envia nada: solo redacta un borrador que el usuario revisa, edita y usa
a su criterio desde su propio correo o WhatsApp.
"""

TEMPLATES = {
    "bodega": (
        "Hola, vi que {name} cuenta con instalaciones de bodega en {city}. "
        "En [tu empresa] ofrecemos servicios de cargue y descargue de "
        "mercancías que pueden agilizar la rotación de su bodega. "
        "¿Les gustaría conocer más detalles?"
    ),
    "almacenamiento": (
        "Hola, vi que {name} cuenta con instalaciones de almacenamiento en "
        "{city}. En [tu empresa] ofrecemos servicios de cargue y descargue "
        "de mercancías. ¿Tendrían un espacio para conversar esta semana?"
    ),
    "distribuidora": (
        "Hola, vi que {name} es una empresa de distribución en {city}. En "
        "[tu empresa] ofrecemos servicios de cargue y descargue que pueden "
        "apoyar su operación de distribución. ¿Les interesaría conocer más?"
    ),
    "mayorista": (
        "Hola, vi que {name} opera como mayorista en {city}. En [tu "
        "empresa] ofrecemos servicios de cargue y descargue de mercancías "
        "pensados para el volumen que manejan. ¿Conversamos esta semana?"
    ),
    "alimentos": (
        "Hola, vi que {name} es una empresa de alimentos en {city}. En [tu "
        "empresa] ofrecemos servicios de cargue y descargue de mercancías, "
        "cuidando los tiempos que requiere su inventario. ¿Les gustaría "
        "conocer más?"
    ),
    "bebidas": (
        "Hola, vi que {name} es una empresa de bebidas en {city}. En [tu "
        "empresa] ofrecemos servicios de cargue y descargue de mercancías "
        "para su operación. ¿Tendrían un espacio para conversar?"
    ),
    "logistica": (
        "Hola, vi que {name} opera en logística en {city}. En [tu empresa] "
        "ofrecemos servicios de cargue y descargue de mercancías que "
        "pueden complementar su operación. ¿Les interesaría conocer más?"
    ),
    "transporte": (
        "Hola, vi que {name} presta servicios de transporte en {city}. En "
        "[tu empresa] ofrecemos cargue y descargue de mercancías como "
        "servicio complementario. ¿Conversamos esta semana?"
    ),
    "importadora": (
        "Hola, vi que {name} es una empresa importadora en {city}. En [tu "
        "empresa] ofrecemos servicios de cargue y descargue para la "
        "recepción de sus mercancías. ¿Les gustaría conocer más?"
    ),
    "comercializadora": (
        "Hola, vi que {name} es una comercializadora en {city}. En [tu "
        "empresa] ofrecemos servicios de cargue y descargue de mercancías. "
        "¿Tendrían un espacio para conversar esta semana?"
    ),
    "industria": (
        "Hola, vi que {name} es una empresa industrial en {city}. En [tu "
        "empresa] ofrecemos servicios de cargue y descargue de materia "
        "prima y producto terminado. ¿Les interesaría conocer más?"
    ),
}

DEFAULT_TEMPLATE = (
    "Hola, encontré a {name} buscando empresas en {city} que puedan "
    "necesitar apoyo logístico. En [tu empresa] ofrecemos servicios de "
    "cargue y descargue de mercancías. ¿Les gustaría conocer más sobre lo "
    "que ofrecemos?"
)


def build_message(company):
    template = TEMPLATES.get(company.category, DEFAULT_TEMPLATE)
    return template.format(name=company.name, city=company.city or "la zona")
