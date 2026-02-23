import re
import functools
from typing import Optional, Tuple
from .constants import ShipClass, SHIP_SPECS, ShipType, SHIP_TRANSLATIONS
from .ship_presets import SHIP_PRESETS

def parse_ship_class(text: str) -> Optional[ShipClass]:
    """Определяет класс корабля из текста"""
    text_lower = text.lower().strip()
    
    for key, value in SHIP_TRANSLATIONS.items():
        if key in text_lower:
            return value
    return None

def calculate_crew_requirements(ship_class: ShipClass) -> int:
    """Возвращает необходимый экипаж для корабля"""
    return SHIP_SPECS[ship_class][1]

def calculate_methane_consumption(ship_class: ShipClass, distance_km: int = 100) -> int:
    """Расчет потребления метана на заданное расстояние"""
    consumption_per_100km = SHIP_SPECS[ship_class][2]
    return int((consumption_per_100km / 100) * distance_km)

def calculate_ship_upkeep(ship_class: ShipClass, current_crew: int) -> Tuple[int, int]:
    """
    Расчет затрат на содержание корабля за ход
    Returns: (зарплата_зр, пайки)
    """
    salary = current_crew * 2  # 2 ЗР на человека
    rations = current_crew * 1  # 1 паек на человека
    return salary, rations

def format_currency(amount: int) -> str:
    """Форматирует сумму в золотые рубли"""
    return f"{amount:,} ЗР".replace(",", " ")

def format_number(amount: int) -> str:
    """Форматирует число с разделителями"""
    return f"{amount:,}".replace(",", " ")

def parse_ship_input(text: str) -> Optional[dict]:
    """
    Парсит строку формата:
    1. "Ударный Корвет пр-к 'Молния' - 'Находчивый'" (Полный)
    2. "Севастополь Призрак" (Упрощенный)
    """
    text = text.strip()
    
    # Сначала пробуем упрощенный формат: "Проект Позывной" или "Проект - Позывной"
    # Проверяем, начинается ли строка с известного проекта
    for project_name in SHIP_PRESETS.keys():
        if text.lower().startswith(project_name.lower()):
            # Нашли проект. Остаток строки - позывной.
            remaining = text[len(project_name):].strip().lstrip('-').strip()
            if not remaining:
                continue # Возможно это просто название проекта без позывного
            
            preset = SHIP_PRESETS[project_name.lower()]
            ship_class = preset["class"]
            specs = SHIP_SPECS[ship_class]
            
            return {
                "ship_class": ship_class,
                "project": project_name.capitalize(),
                "callsign": remaining.strip('"\''),
                "current_crew": specs[1],
                "required_crew": specs[1],
                "status": "в_строю"
            }

    # Если не подошло, пробуем классический регулярный парсинг
    pattern = r'([а-яА-Я\s]+)\s+пр-к\s*["\']?([^"\']+)["\']?\s*-\s*["\']?([^"\']+)["\']?(?:\s*-\s*(\d+)/(\d+)\s*-\s*([а-яА-Я\s]+))?'
    
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    
    ship_type_str = match.group(1).strip()
    project = match.group(2).strip()
    callsign = match.group(3).strip()

    ship_class = parse_ship_class(ship_type_str)
    if not ship_class:
        # Может быть проект известен?
        if project.lower() in SHIP_PRESETS:
            ship_class = SHIP_PRESETS[project.lower()]["class"]
        else:
            return None
    
    # Проверяем наличие опциональных групп
    if match.group(4) and match.group(5) and match.group(6):
        current_crew = int(match.group(4))
        required_crew = int(match.group(5))
        status = match.group(6).strip()
    else:
        # Значения по умолчанию
        specs = SHIP_SPECS[ship_class]
        required_crew = specs[1]
        current_crew = required_crew
        status = "в_строю"
    
    return {
        "ship_class": ship_class,
        "project": project,
        "callsign": callsign,
        "current_crew": current_crew,
        "required_crew": required_crew,
        "status": status
    }


def requires_fleet(func):
    """Декоратор: проверяет наличие флотилии у игрока и передаёт её через ctx.fleet"""
    @functools.wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии. Используйте `!анкета` для регистрации.")
            return
        ctx.fleet = fleet
        return await func(self, ctx, *args, **kwargs)
    return wrapper

