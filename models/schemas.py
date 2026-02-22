from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json

class ShipStatus(str, Enum):
    OPERATIONAL = "в_строю"
    LIGHT_DAMAGE = "легкие_повреждения"
    MODERATE_DAMAGE = "средние_повреждения"
    HEAVY_DAMAGE = "тяжелые_повреждения"
    CRITICAL_DAMAGE = "критические_повреждения"
    DESTROYED = "уничтожен"

class ModuleType(str, Enum):
    HULL = "корпус"
    ENGINE = "двигатель"
    WEAPON = "оружие"
    AMMO = "боеукладка"
    ARMOR = "броня"
    FUEL_TANK = "топливный_бак"
    OTHER = "прочее"

class Module(BaseModel):
    id: int
    name: str
    type: ModuleType
    weight: int
    price: int
    stats: Dict[str, Any] = {}  # {thrust: 100, damage: 50, etc.}

    class Config:
        from_attributes = True

class ShipModule(BaseModel):
    id: Optional[int] = None
    ship_id: int
    module_id: int
    count: int = 1
    module: Optional[Module] = None # For joined queries

    class Config:
        from_attributes = True

class Ship(BaseModel):
    id: Optional[int] = None
    fleet_id: int
    ship_class: str
    project: str
    callsign: str
    current_crew: int
    required_crew: int
    status: ShipStatus
    modules: List[ShipModule] = []
    created_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def total_hp(self) -> int:
        # Base HP from hull + armor bonuses
        # Simple formula for now: crew * 10 + armor HP
        hp = self.current_crew * 10
        for sm in self.modules:
            if sm.module:
                hp += sm.module.stats.get("hp_bonus", 0) * sm.count
        return hp

    @property
    def total_weight(self) -> int:
        weight = 0
        for sm in self.modules:
            if sm.module:
                weight += sm.module.weight * sm.count
        # Base weight from class/crew? Let's rely on modules for now or add a base.
        return weight

    @property
    def total_thrust(self) -> int:
        thrust = 0
        for sm in self.modules:
            if sm.module and sm.module.type == ModuleType.ENGINE:
                thrust += sm.module.stats.get("thrust", 0) * sm.count
        return thrust

    @property
    def evasion(self) -> float:
        # Evasion based on TWR (Thrust-to-Weight Ratio)
        if self.total_weight == 0: return 0.0
        twr = self.total_thrust / self.total_weight
        # Base evasion + TWR bonus. Cap at some value.
        return min(0.1 + (twr * 0.1), 0.6) # 10% base + 10% per TWR unit, max 60%

    @property
    def is_flyable(self) -> bool:
        return self.total_thrust >= self.total_weight

    class Config:
        from_attributes = True

class Fleet(BaseModel):
    id: Optional[int] = None
    user_id: int
    guild_id: int
    name: str
    leader_name: str
    gold: int = 10000
    rations: int = 0
    methane: int = 0
    turn_count: int = 0
    location: str = "Столица"
    location_spec: str = "База Флота" # Торговцы, Наемники, etc.
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True

class FleetWithShips(Fleet):
    ships: List[Ship] = []
    
    @property
    def total_crew(self) -> int:
        return sum(ship.current_crew for ship in self.ships)
    
    @property
    def required_crew(self) -> int:
        return sum(ship.required_crew for ship in self.ships)
    
    @property
    def salary_per_turn(self) -> int:
        from utils.constants import SALARY_PER_CREW
        return self.total_crew * SALARY_PER_CREW
    
    @property
    def rations_per_turn(self) -> int:
        from utils.constants import RATIONS_PER_CREW
        return self.total_crew * RATIONS_PER_CREW
    
    @property
    def methane_per_100km(self) -> int:
        """Расчёт метана: вес / тяга * базовый расход класса. Fallback на SHIP_SPECS."""
        total = 0
        from utils.constants import SHIP_SPECS, ShipClass
        for ship in self.ships:
            # Попытка модульного расчёта: масса / тяга определяет эффективность
            if ship.modules and ship.total_thrust > 0:
                # Тяжелее корабль → больше расход. Эффективнее двигатель → меньше.
                weight_factor = ship.total_weight / ship.total_thrust
                base_consumption = ship.total_weight * 0.01  # 1% массы на 100km
                total += int(base_consumption * weight_factor)
            else:
                # Legacy fallback
                try:
                    ship_enum = ShipClass(ship.ship_class)
                    total += SHIP_SPECS.get(ship_enum, (None, 0, 0, 0))[2]
                except (ValueError, KeyError):
                    pass
        return total
    
    def to_discord_embed(self) -> dict:
        """Форматирует флот в Embed для Discord"""
        from utils.constants import STATUS_EMOJIS, ShipClass
        
        ships_text = []
        for ship in self.ships:
            emoji = STATUS_EMOJIS.get(ship.status, "⚪")
            fly_status = "✈️" if ship.is_flyable else "⚠️ Перегруз"
            
            # Show simplified stats
            ships_text.append(
                f"{emoji} **{ship.ship_class}** \"{ship.callsign}\" {fly_status}\n"
                f"├ HP: {ship.total_hp} | TWR: {ship.total_thrust}/{ship.total_weight}\n"
                f"└ Статус: {ship.status.value}"
            )
        
        ships_str = "\n\n".join(ships_text) if ships_text else "*Флот пуст*"
        
        return {
            "title": f"⚓ {self.name}",
            "description": f"**Тархан:** {self.leader_name}\n**Ход:** {self.turn_count}\n📍 **{self.location}** ({self.location_spec})",
            "fields": [
                {
                    "name": "💰 Экономика",
                    "value": (
                        f"Золотые рубли: `{self.gold:,}` / `-{self.salary_per_turn:,}` за ход\n"
                        f"Пайки: `{self.rations:,}` / `-{self.rations_per_turn:,}` за ход\n"
                        f"Метан: `{self.methane:,}` тонн"
                    ),
                    "inline": False
                },
                {
                    "name": "👥 Личный состав",
                    "value": f"Всего: `{self.total_crew:,}` / `{self.required_crew:,}` требуется",
                    "inline": False
                },
                {
                    "name": "🚀 Состав флота",
                    "value": ships_str[:1024] if len(ships_str) <= 1024 else ships_str[:1021] + "...",
                    "inline": False
                }
            ],
            "color": 0x3498db,
            "footer": {"text": f"ID Флота: {self.id} • Обновлено"}
        }
