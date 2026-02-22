from enum import Enum
from typing import Dict, Tuple
from models.schemas import ShipStatus

class ShipType(str, Enum):
    CORVETTE = "корвет"
    FRIGATE = "фрегат"
    CRUISER = "крейсер"

class ShipClass(str, Enum):
    STRIKE_CORVETTE = "ударный_корвет"
    ARTILLERY_FRIGATE = "артиллерийский_фрегат"
    HEAVY_CRUISER = "тяжелый_крейсер"

# DamageStatus удалён — используется ShipStatus из models.schemas

# Характеристики кораблей: (тип, экипаж, метан/100км, базовая_цена)
SHIP_SPECS: Dict[ShipClass, Tuple[ShipType, int, int, int]] = {
    ShipClass.STRIKE_CORVETTE: (ShipType.CORVETTE, 10, 20, 500),
    ShipClass.ARTILLERY_FRIGATE: (ShipType.FRIGATE, 50, 50, 2000),
    ShipClass.HEAVY_CRUISER: (ShipType.CRUISER, 400, 200, 10000),
}

SHIP_TRANSLATIONS: Dict[str, ShipClass] = {
    "ударный корвет": ShipClass.STRIKE_CORVETTE,
    "артиллерийский фрегат": ShipClass.ARTILLERY_FRIGATE,
    "тяжелый крейсер": ShipClass.HEAVY_CRUISER,
    "корвет": ShipClass.STRIKE_CORVETTE,
    "фрегат": ShipClass.ARTILLERY_FRIGATE,
    "крейсер": ShipClass.HEAVY_CRUISER,
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
