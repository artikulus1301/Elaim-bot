from .constants import ShipClass

# Формат: [Имя модуля в БД, количество]
# Используем частичное совпадение имен из списка БД

SHIP_PRESETS = {
    "sevastopol": {
        "class": ShipClass.HEAVY_CRUISER,
        "loadout": [
            ("МК-6-180", 2), ("МК-2-180", 2), ("2А37", 6), 
            ("Р-9 \"Спринт\"", 12), ("НК-30", 4), ("Топливный бак", 8),
            ("Усиленная обшивка", 4), ("Сталь-1", 4)
        ]
    },
    "varyag": {
        "class": ShipClass.HEAVY_CRUISER,
        "loadout": [
            ("МК-2-180", 4), ("2А37", 4), ("НК-30", 4), 
            ("Топливный бак", 6), ("Сталь-1", 6)
        ]
    },
    "nomad": {
        "class": ShipClass.CRUISER,
        "loadout": [
            ("МК-2-180", 2), ("Д-30С", 4), ("Топливный бак", 12),
            ("Сталь-1", 2)
        ]
    },
    "negev": {
        "class": ShipClass.HEAVY_CRUISER,
        "loadout": [
            ("МК-2-180", 4), ("НК-30", 4), ("Топливный бак", 4),
            ("Сталь-1", 10), ("АСО-75", 2)
        ]
    },
    "gladiator": {
        "class": ShipClass.HEAVY_FRIGATE,
        "loadout": [
            ("Д-80 \"Молот\"", 2), ("2А37", 2), ("Р-5 \"Зенит\"", 2),
            ("Д-30С", 2), ("Топливный бак", 2), ("Сталь-1", 4)
        ]
    },
    "lightning": {
        "class": ShipClass.INTERCEPTOR,
        "loadout": [
            ("АК-100", 2), ("РД-51", 2), ("Топливный бак", 1)
        ]
    },
    "paladin": {
        "class": ShipClass.HEAVY_FRIGATE,
        "loadout": [
            ("АК-100", 2), ("2А37", 2), ("Д-30С", 2), 
            ("Топливный бак", 2), ("Сталь-1", 6)
        ]
    },
    "intrepid": {
        "class": ShipClass.HEAVY_CORVETTE,
        "loadout": [
            ("АК-100", 4), ("Д-30С", 2), ("Топливный бак", 2),
            ("Сталь-1", 2)
        ]
    },
    "navarin": {
        "class": ShipClass.CORVETTE,
        "loadout": [
            ("АК-725", 4), ("Р-5 \"Зенит\"", 2), ("РД-51", 2),
            ("Топливный бак", 1), ("Сталь-1", 1)
        ]
    },
    "skylark": {
        "class": ShipClass.TANKER,
        "loadout": [
            ("Д-30С", 2), ("Топливный бак", 10), ("АСО-75", 1)
        ]
    },
    "fenek": {
        "class": ShipClass.AA_CORVETTE,
        "loadout": [
            ("2А37", 1), ("Р-9 \"Спринт\"", 4), ("РД-51", 1),
            ("Топливный бак", 1)
        ]
    },
    "gepard": {
        "class": ShipClass.AA_FRIGATE,
        "loadout": [
            ("2А37", 6), ("Р-9 \"Спринт\"", 8), ("Д-30С", 2),
            ("Топливный бак", 2), ("Сталь-1", 2)
        ]
    },
    "mockingbird": {
        "class": ShipClass.LIGHT_TANKER,
        "loadout": [
            ("РД-51", 1), ("Топливный бак", 4)
        ]
    },
    "longbow": {
        "class": ShipClass.HEAVY_CARRIER,
        "loadout": [
            ("НК-30", 4), ("Топливный бак", 8), ("Сталь-1", 4)
        ]
    },
    "wasp": {
        "class": ShipClass.LIGHT_CARRIER,
        "loadout": [
            ("Д-30С", 2), ("Топливный бак", 4), ("Сталь-1", 2)
        ]
    },
    "typhon": {
        "class": ShipClass.MISSILE_CRUISER,
        "loadout": [
            ("Ракетная шахта", 6), ("Крылатая ракета Х-15", 3), ("Тактическая ракета А-100", 3),
            ("НК-30", 4), ("Топливный бак", 6), ("Сталь-1", 4)
        ]
    },
    "yars": {
        "class": ShipClass.MISSILE_CORVETTE,
        "loadout": [
            ("Ракетная шахта", 2), ("Крылатая ракета Х-15", 2),
            ("РД-51", 2), ("Топливный бак", 1)
        ]
    }
}
