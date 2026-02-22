from typing import Dict, List, Tuple
import random
from models.schemas import Ship, ModuleType, ShipStatus

# --- MODULE DEFINITIONS (Prototypes) ---
# In a real app these might be in the DB, but for simplicity we define them here
# to populate the DB on startup or use as reference.

MODULE_PROTOTYPES = [
    # --- ENGINES ---
    {"name": "Двигатель РД-51", "type": ModuleType.ENGINE, "weight": 200, "price": 500, "stats": {"thrust": 400}},
    {"name": "Двигатель НК-30", "type": ModuleType.ENGINE, "weight": 150, "price": 300, "stats": {"thrust": 250}},
    {"name": "Двигатель Д-30С", "type": ModuleType.ENGINE, "weight": 300, "price": 800, "stats": {"thrust": 600}},
    {"name": "Маневровый Д-10", "type": ModuleType.ENGINE, "weight": 50, "price": 100, "stats": {"thrust": 80}},

    # --- WEAPONS (Missiles) ---
    {"name": "Р-5 \"Зенит\"", "type": ModuleType.WEAPON, "weight": 200, "price": 600, 
     "stats": {"damage": 600, "accuracy": 0.95, "shots": 1, "ammo_type": "missile", "desc": "Автонаводка (ИК)"}},
    {"name": "Р-9 \"Спринт\"", "type": ModuleType.WEAPON, "weight": 100, "price": 300, 
     "stats": {"damage": 300, "accuracy": 0.9, "shots": 1, "ammo_type": "missile", "desc": "РЛС наведение"}},
    {"name": "Р-6 \"Надир\"", "type": ModuleType.WEAPON, "weight": 150, "price": 400, 
     "stats": {"damage": 400, "accuracy": 0.9, "shots": 1, "ammo_type": "missile", "desc": "Тактическая ракета"}},
    {"name": "ФАБ-1000", "type": ModuleType.WEAPON, "weight": 1000, "price": 200, 
     "stats": {"damage": 1000, "accuracy": 0.6, "shots": 1, "ammo_type": "bomb", "desc": "Неуправляемая бомба"}},
    {"name": "Крылатая ракета Х-15", "type": ModuleType.WEAPON, "weight": 500, "price": 1500, 
     "stats": {"damage": 1200, "accuracy": 0.85, "shots": 1, "ammo_type": "missile"}},
    {"name": "Крылатая ракета Х-15Р", "type": ModuleType.WEAPON, "weight": 550, "price": 1100, 
     "stats": {"damage": 1000, "accuracy": 0.9, "shots": 1, "ammo_type": "missile", "desc": "Улучшенное наведение"}},
    {"name": "Крылатая ракета Х-15ПН", "type": ModuleType.WEAPON, "weight": 600, "price": 4000, 
     "stats": {"damage": 2500, "accuracy": 0.95, "shots": 1, "ammo_type": "missile", "desc": "Ядерная БЧ"}},
    {"name": "Тактическая ракета А-100", "type": ModuleType.WEAPON, "weight": 800, "price": 1500, 
     "stats": {"damage": 1500, "accuracy": 0.8, "shots": 1, "ammo_type": "missile"}},
    
    # --- WEAPONS (Autocannons) ---
    {"name": "2А37 (30мм)", "type": ModuleType.WEAPON, "weight": 150, "price": 3000, 
     "stats": {"damage": 40, "accuracy": 0.85, "shots": 10, "desc": "Скорострельная пушка"}},
    {"name": "АК-725 (57мм)", "type": ModuleType.WEAPON, "weight": 300, "price": 1500, 
     "stats": {"damage": 100, "accuracy": 0.8, "shots": 4}},
    {"name": "АК-100 (100мм)", "type": ModuleType.WEAPON, "weight": 500, "price": 2000, 
     "stats": {"damage": 250, "accuracy": 0.75, "shots": 2}},
    {"name": "Палаш-1", "type": ModuleType.WEAPON, "weight": 200, "price": 1200, 
     "stats": {"damage": 20, "accuracy": 0.95, "shots": 20, "desc": "Система ПРО (APS)"}},

    # --- WEAPONS (Artillery) ---
    {"name": "Д-80 \"Молот\"", "type": ModuleType.WEAPON, "weight": 1200, "price": 4000, 
     "stats": {"damage": 800, "accuracy": 0.6, "shots": 1, "desc": "Тяжелая гаубица"}},
    {"name": "МК-1-180 (180мм)", "type": ModuleType.WEAPON, "weight": 1500, "price": 4000, 
     "stats": {"damage": 600, "accuracy": 0.7, "shots": 1}},
    {"name": "МК-2-180 (Спарка)", "type": ModuleType.WEAPON, "weight": 2500, "price": 6000, 
     "stats": {"damage": 600, "accuracy": 0.65, "shots": 2}},
    {"name": "МК-6-180 (Батарея)", "type": ModuleType.WEAPON, "weight": 6000, "price": 24000, 
     "stats": {"damage": 600, "accuracy": 0.6, "shots": 6, "desc": "Залповая система"}},

    # --- WEAPONS (MLRS) ---
    {"name": "РСЗО А-220", "type": ModuleType.WEAPON, "weight": 2000, "price": 4000, 
     "stats": {"damage": 150, "accuracy": 0.5, "shots": 20, "desc": "Реактивная система"}},

    # --- HULL/ARMOR ---
    {"name": "Усиленная обшивка", "type": ModuleType.HULL, "weight": 1000, "price": 2000, "stats": {"hp_bonus": 500}},
    {"name": "Бронеплита Сталь-1", "type": ModuleType.ARMOR, "weight": 200, "price": 400, "stats": {"hp_bonus": 100}},
    
    # --- UTILITY ---
    {"name": "Топливный бак (Малый)", "type": ModuleType.FUEL_TANK, "weight": 50, "price": 200, "stats": {"capacity": 100}},
    {"name": "Боеукладка", "type": ModuleType.AMMO, "weight": 100, "price": 300, "stats": {"capacity": 50, "explosive": True}},
    {"name": "АСО-75", "type": ModuleType.AMMO, "weight": 50, "price": 100, "stats": {"capacity": 20, "desc": "Ловушки"}}
]

async def seed_modules(db):
    """Populates the database with initial modules if empty"""
    existing = await db.get_all_modules()
    existing_names = {m['name'] for m in existing}
    
    import json
    async with db.get_db() as conn:
        for mod in MODULE_PROTOTYPES:
            if mod["name"] not in existing_names:
                await conn.execute(
                    "INSERT INTO modules (name, type, weight, price, stats) VALUES (?, ?, ?, ?, ?)",
                    (mod["name"], mod["type"].value, mod["weight"], mod["price"], json.dumps(mod["stats"]))
                )
        await conn.commit()

# --- COMBAT MECHANICS ---

def calculate_ship_combat_stats(ship: Ship) -> dict:
    """Aggregates ship stats for combat"""
    total_hp = ship.total_hp
    evasion = ship.evasion
    
    weapons = []
    for sm in ship.modules:
        if sm.module and sm.module.type == ModuleType.WEAPON:
            # Add weapon instance for each count
            for _ in range(sm.count):
                w_stats = sm.module.stats.copy()
                w_stats['name'] = sm.module.name # Include name for logs
                weapons.append(w_stats)
    
    return {
        "hp": total_hp,
        "evasion": evasion,
        "weapons": weapons,
        "callsign": ship.callsign,
        "id": ship.id
    }

def simulate_volley(attacker_stats: dict, defender_stats: dict) -> Tuple[List[str], int]:
    """
    Simulates one volley from attacker to defender.
    Returns (logs, total_damage)
    """
    logs = []
    attacker_name = attacker_stats['callsign']
    defender_name = defender_stats['callsign']
    defender_evasion = defender_stats.get('evasion', 0.0)
    
    total_damage = 0
    
    if not attacker_stats['weapons']:
         logs.append(f"⚠️ **{attacker_name}** не имеет вооружения!")
         return logs, 0

    for weapon in attacker_stats['weapons']:
        # Weapon stats
        dmg = weapon.get("damage", 10)
        acc = weapon.get("accuracy", 0.5)
        shots = weapon.get("shots", 1)
        w_name = weapon.get("name", "Орудие")
        
        hits = 0
        for _ in range(shots):
            # Hit chance = Weapon Accuracy - Defender Evasion
            # Example: Acc 0.8 - Eva 0.2 = 0.6 (60%)
            # If evasion is high, hit chance drops.
            hit_chance = acc - defender_evasion
            if hit_chance < 0.05: hit_chance = 0.05 # Min 5% chance
            
            if random.random() < hit_chance:
                hits += 1
        
        if hits > 0:
            volley_dmg = hits * dmg
            total_damage += volley_dmg
            logs.append(f"💥 **{attacker_name}** ({w_name}) попал {hits}/{shots} раз по **{defender_name}**! Урон: {volley_dmg}")
        else:
            logs.append(f"💨 **{attacker_name}** ({w_name}) промахнулся по **{defender_name}**!")
            
    return logs, total_damage

def generate_debris_field(ships: List[Ship], guaranteed_weapons: bool = False) -> List[dict]:
    """
    Generates debris from destroyed/damaged ships for the "Battlefield" menu.
    """
    debris = []
    
    for ship in ships:
        # 1. Fuel Debris
        if random.random() < 0.6:
            debris.append({
                "type": "resource",
                "name": "Топливо",
                "amount": random.randint(50, 500), # Tons
                "modifier": "explosive" if random.random() < 0.3 else None,
                "timer": random.randint(30, 60) # Seconds to explosion
            })
            
        # 2. Ammo/Weapon Debris
        if random.random() < 0.4:
             debris.append({
                "type": "resource",
                "name": "Боеприпасы",
                "amount": random.randint(10, 50),
                "modifier": "explosive" if random.random() < 0.4 else "radiation" if random.random() < 0.2 else None,
                "timer": random.randint(30, 50)
            })

        # 3. Module Debris
        for sm in ship.modules:
            if not sm.module: continue
            
            # Guaranteed weapons check
            is_guaranteed = guaranteed_weapons and sm.module.type == ModuleType.WEAPON
            
            if is_guaranteed or random.random() < 0.25: # 25% chance otherwise
                 debris.append({
                     "type": "module",
                     "module_id": sm.module.id,
                     "name": sm.module.name,
                     "modifier": "radiation" if random.random() < 0.3 and not is_guaranteed else None,
                     "timer": 60 
                 })
                 
    return debris
