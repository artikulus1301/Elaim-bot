from enum import Enum
from typing import Dict, Tuple
from models.schemas import ShipStatus

class ShipType(str, Enum):
    CORVETTE = "корвет"
    FRIGATE = "фрегат"
    CRUISER = "крейсер"
    TANKER = "танкер"
    SUPPORT = "поддержка"
    CARRIER = "авианосец"
    MISSILE_SHIP = "ракетный_корабль"

class ShipClass(str, Enum):
    STRIKE_CORVETTE = "ударный_корвет"
    ARTILLERY_FRIGATE = "артиллерийский_фрегат"
    HEAVY_CRUISER = "тяжелый_крейсер"
    CRUISER = "крейсер"
    INTERCEPTOR = "перехватчик"
    HEAVY_FRIGATE = "тяжелый_фрегат"
    HEAVY_CORVETTE = "тяжелый_корвет"
    CORVETTE = "корвет"
    TANKER = "танкер"
    LIGHT_TANKER = "малый_танкер"
    AA_CORVETTE = "пво_корвет"
    AA_FRIGATE = "пво_фрегат"
    HEAVY_CARRIER = "тяжелый_авианосец"
    LIGHT_CARRIER = "легкий_авианосец"
    MISSILE_CRUISER = "ракетный_крейсер"
    MISSILE_CORVETTE = "ракетный_корвет"

# DamageStatus удалён — используется ShipStatus из models.schemas

# Характеристики кораблей: (тип, экипаж, метан/100км, базовая_цена)
SHIP_SPECS: Dict[ShipClass, Tuple[ShipType, int, int, int]] = {
    ShipClass.STRIKE_CORVETTE: (ShipType.CORVETTE, 10, 20, 500),
    ShipClass.ARTILLERY_FRIGATE: (ShipType.FRIGATE, 50, 50, 2000),
    ShipClass.HEAVY_CRUISER: (ShipType.CRUISER, 400, 200, 10000),
    ShipClass.CRUISER: (ShipType.CRUISER, 200, 150, 7000),
    ShipClass.INTERCEPTOR: (ShipType.CORVETTE, 8, 15, 400),
    ShipClass.HEAVY_FRIGATE: (ShipType.FRIGATE, 60, 60, 2500),
    ShipClass.HEAVY_CORVETTE: (ShipType.CORVETTE, 20, 30, 800),
    ShipClass.CORVETTE: (ShipType.CORVETTE, 15, 25, 600),
    ShipClass.TANKER: (ShipType.TANKER, 30, 40, 1500),
    ShipClass.LIGHT_TANKER: (ShipType.TANKER, 10, 15, 500),
    ShipClass.AA_CORVETTE: (ShipType.SUPPORT, 12, 20, 700),
    ShipClass.AA_FRIGATE: (ShipType.SUPPORT, 40, 50, 1800),
    ShipClass.HEAVY_CARRIER: (ShipType.CARRIER, 500, 250, 15000),
    ShipClass.LIGHT_CARRIER: (ShipType.CARRIER, 150, 100, 6000),
    ShipClass.MISSILE_CRUISER: (ShipType.MISSILE_SHIP, 300, 180, 12000),
    ShipClass.MISSILE_CORVETTE: (ShipType.MISSILE_SHIP, 25, 30, 1000),
}

SHIP_TRANSLATIONS: Dict[str, ShipClass] = {
    "тяжелый крейсер": ShipClass.HEAVY_CRUISER,
    "крейсер": ShipClass.CRUISER,
    "артиллерийский фрегат": ShipClass.ARTILLERY_FRIGATE,
    "тяжелый фрегат": ShipClass.HEAVY_FRIGATE,
    "фрегат пво": ShipClass.AA_FRIGATE,
    "фрегат": ShipClass.ARTILLERY_FRIGATE,
    "тяжелый корвет": ShipClass.HEAVY_CORVETTE,
    "пво корвет": ShipClass.AA_CORVETTE,
    "ударный корвет": ShipClass.STRIKE_CORVETTE,
    "корвет": ShipClass.CORVETTE,
    "перехватчик": ShipClass.INTERCEPTOR,
    "малый корвет": ShipClass.INTERCEPTOR,
    "танкер": ShipClass.TANKER,
    "малый танкер": ShipClass.LIGHT_TANKER,
    "тяжелый авианосец": ShipClass.HEAVY_CARRIER,
    "легкий авианосец": ShipClass.LIGHT_CARRIER,
    "авианосец": ShipClass.LIGHT_CARRIER,
    "ракетный крейсер": ShipClass.MISSILE_CRUISER,
    "ракетный корвет": ShipClass.MISSILE_CORVETTE,
}

STATUS_EMOJIS = {
    ShipStatus.OPERATIONAL: "🟢",
    ShipStatus.LIGHT_DAMAGE: "🟡",
    ShipStatus.MODERATE_DAMAGE: "🟠",
    ShipStatus.HEAVY_DAMAGE: "🔴",
    ShipStatus.CRITICAL_DAMAGE: "⚫",
    ShipStatus.DESTROYED: "💀",
}

# === ИГРОВАЯ ЭКОНОМИКА ===

# Содержание экипажа (за ход)
SALARY_PER_CREW = 2       # ЗР на человека
RATIONS_PER_CREW = 1      # Пайки на человека

# Цены ресурсов (базовые)
RATIONS_BASE_PRICE = 10   # ЗР за 1 паёк
METHANE_BASE_PRICE = 5    # ЗР за 1 тонну метана

# Скидки по локациям
DISCOUNT_FLEET_BASE = 0.7       # База Флота: -30%
DISCOUNT_FUEL_DEPOT = 0.5       # Топливохранилище: метан -50%
SELL_PRICE_MULTIPLIER = 0.5     # Продажа: 50% от стоимости

# Боевая система
MAX_BATTLE_TURNS = 10
MAX_BATTLE_DISTANCE = 20
RETREAT_CHANCE = 0.5
MIN_HIT_CHANCE = 0.05

# Стартовые ресурсы
STARTING_GOLD = 10000
STARTING_RATIONS = 100
STARTING_METHANE = 200

# Пагинация
SHOP_ITEMS_PER_PAGE = 8
