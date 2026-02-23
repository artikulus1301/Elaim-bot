import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime
import aiosqlite
from models.schemas import Fleet, FleetWithShips, Ship, ShipModule, Module, ShipStatus

logger = logging.getLogger('elaim_bot')


def parse_datetime(value):
    """Parse datetime from SQLite timestamp string"""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # SQLite timestamp format: YYYY-MM-DD HH:MM:SS
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # ISO format
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return datetime.now()
    return datetime.now()


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    @asynccontextmanager
    async def get_db(self):
        """Get an async database connection context manager"""
        async with aiosqlite.connect(self.db_path) as db:
            yield db

    async def init_db(self):
        """Initialize database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS modules (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL,
                    weight INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    stats TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS fleets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    leader_name TEXT NOT NULL DEFAULT '',
                    gold INTEGER NOT NULL DEFAULT 10000,
                    rations INTEGER NOT NULL DEFAULT 0,
                    methane INTEGER NOT NULL DEFAULT 0,
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    location TEXT NOT NULL DEFAULT 'Столица',
                    location_spec TEXT NOT NULL DEFAULT 'База Флота',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, guild_id)
                );

                CREATE TABLE IF NOT EXISTS ships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fleet_id INTEGER NOT NULL,
                    ship_class TEXT NOT NULL,
                    project TEXT NOT NULL,
                    callsign TEXT NOT NULL,
                    current_crew INTEGER NOT NULL,
                    required_crew INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'в_строю',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (fleet_id) REFERENCES fleets(id),
                    UNIQUE(fleet_id, callsign)
                );

                CREATE TABLE IF NOT EXISTS ship_modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ship_id INTEGER NOT NULL,
                    module_id INTEGER NOT NULL,
                    count INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (ship_id) REFERENCES ships(id),
                    FOREIGN KEY (module_id) REFERENCES modules(id),
                    UNIQUE(ship_id, module_id)
                );

                CREATE TABLE IF NOT EXISTS user_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    battles_won INTEGER DEFAULT 0,
                    battles_lost INTEGER DEFAULT 0,
                    ships_destroyed INTEGER DEFAULT 0,
                    total_damage_dealt INTEGER DEFAULT 0,
                    credits INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS fleet_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fleet_id INTEGER NOT NULL,
                    module_id INTEGER NOT NULL,
                    count INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (fleet_id) REFERENCES fleets(id),
                    FOREIGN KEY (module_id) REFERENCES modules(id),
                    UNIQUE(fleet_id, module_id)
                );
            """)
            await db.commit()
            logger.info("Database initialized successfully")

    async def get_module(self, module_id: int) -> Optional[Dict[str, Any]]:
        """Get module by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, name, type, weight, price, stats FROM modules WHERE id = ?",
                (module_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def get_all_modules(self) -> List[Dict[str, Any]]:
        """Get all modules"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id, name, type, weight, price, stats FROM modules") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def add_module(self, name: str, type: str, weight: int, price: int, stats: Dict[str, Any] = None) -> int:
        """Add a new module"""
        if stats is None:
            stats = {}
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO modules (name, type, weight, price, stats) VALUES (?, ?, ?, ?, ?)",
                (name, type, weight, price, json.dumps(stats))
            )
            await db.commit()
            return cursor.lastrowid

    async def create_fleet(self, user_id: int, guild_id: int, name: str, leader_name: str) -> Fleet:
        """Create a new fleet for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO fleets (user_id, guild_id, name, leader_name, gold, rations, methane, turn_count, location, location_spec)
                   VALUES (?, ?, ?, ?, 10000, 0, 0, 0, 'Столица', 'База Флота')""",
                (user_id, guild_id, name, leader_name)
            )
            await db.commit()
            fleet_id = cursor.lastrowid
            return await self.get_fleet(fleet_id)

    async def get_user_fleet(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's fleet"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, user_id, name, created_at FROM fleets WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def get_ship(self, ship_id: int) -> Optional[Ship]:
        """Get a ship by ID with its modules"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT id, fleet_id, ship_class, project, callsign, current_crew, 
                   required_crew, status, created_at FROM ships WHERE id = ?""",
                (ship_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                
                ship_dict = dict(row)
                # Get modules for this ship
                modules_data = await self.get_ship_modules(row['id'])
                ship_modules = []
                for mod_data in modules_data:
                    module = Module(
                        id=mod_data['module_id'],
                        name=mod_data['name'],
                        type=mod_data['type'],
                        weight=mod_data['weight'],
                        price=mod_data['price'],
                        stats=json.loads(mod_data['stats']) if isinstance(mod_data['stats'], str) else mod_data['stats']
                    )
                    ship_modules.append(ShipModule(
                        id=mod_data['id'],
                        ship_id=row['id'],
                        module_id=mod_data['module_id'],
                        count=mod_data['count'],
                        module=module
                    ))
                ship_dict['modules'] = ship_modules
                # Parse datetime if present
                if ship_dict.get('created_at'):
                    ship_dict['created_at'] = parse_datetime(ship_dict['created_at'])
                return Ship(**ship_dict)

    async def add_ship(self, fleet_id: int, ship_class: str, project: str, callsign: str,
                      current_crew: int, required_crew: int, status: str = "в_строю") -> Ship:
        """Add a ship to a fleet"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO ships (fleet_id, ship_class, project, callsign, 
                   current_crew, required_crew, status) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (fleet_id, ship_class, project, callsign, current_crew, required_crew, status)
            )
            await db.commit()
            ship_id = cursor.lastrowid
            return await self.get_ship(ship_id)

    async def add_module_to_ship(self, ship_id: int, module_id: int, count: int = 1) -> int:
        """Add a module to a ship"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO ship_modules (ship_id, module_id, count) VALUES (?, ?, ?)",
                (ship_id, module_id, count)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_fleet_ships(self, fleet_id: int) -> List[Dict[str, Any]]:
        """Get all ships in a fleet"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, fleet_id, ship_class, project, callsign, current_crew, required_crew, status, created_at FROM ships WHERE fleet_id = ?",
                (fleet_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_ship_modules(self, ship_id: int) -> List[Dict[str, Any]]:
        """Get all modules of a ship with their details"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT sm.id, sm.ship_id, sm.module_id, sm.count, 
                   m.name, m.type, m.weight, m.price, m.stats
                   FROM ship_modules sm 
                   JOIN modules m ON sm.module_id = m.id 
                   WHERE sm.ship_id = ?""",
                (ship_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_stats WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def update_user_stats(self, user_id: int, **kwargs) -> None:
        """Update user statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if user exists
            async with db.execute("SELECT id FROM user_stats WHERE user_id = ?", (user_id,)) as cursor:
                exists = await cursor.fetchone()
            
            if not exists:
                # Create new record
                await db.execute(
                    "INSERT INTO user_stats (user_id) VALUES (?)",
                    (user_id,)
                )
            
            # Update stats
            update_fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            await db.execute(
                f"UPDATE user_stats SET {update_fields} WHERE user_id = ?",
                values
            )
            await db.commit()

    async def get_fleet_by_user(self, user_id: int, guild_id: int) -> Optional[Fleet]:
        """Get fleet by user_id and guild_id"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT id, user_id, guild_id, name, leader_name, gold, rations, methane, 
                   turn_count, location, location_spec, created_at, updated_at 
                   FROM fleets WHERE user_id = ? AND guild_id = ?""",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    row_dict = dict(row)
                    # Parse datetime fields
                    if row_dict.get('created_at'):
                        row_dict['created_at'] = parse_datetime(row_dict['created_at'])
                    if row_dict.get('updated_at'):
                        row_dict['updated_at'] = parse_datetime(row_dict['updated_at'])
                    return Fleet(**row_dict)
        return None

    async def get_fleet(self, fleet_id: int) -> Optional[Fleet]:
        """Get fleet by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT id, user_id, guild_id, name, leader_name, gold, rations, methane, 
                   turn_count, location, location_spec, created_at, updated_at 
                   FROM fleets WHERE id = ?""",
                (fleet_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    row_dict = dict(row)
                    # Parse datetime fields
                    if row_dict.get('created_at'):
                        row_dict['created_at'] = parse_datetime(row_dict['created_at'])
                    if row_dict.get('updated_at'):
                        row_dict['updated_at'] = parse_datetime(row_dict['updated_at'])
                    return Fleet(**row_dict)
        return None

    async def get_fleet_with_ships(self, fleet_id: int) -> Optional[FleetWithShips]:
        """Get fleet with all ships and their modules"""
        fleet = await self.get_fleet(fleet_id)
        if not fleet:
            return None
        
        ships_data = await self.get_ships_by_fleet(fleet_id)
        return FleetWithShips(**fleet.dict(), ships=ships_data)

    async def get_ships_by_fleet(self, fleet_id: int) -> List[Ship]:
        """Get all ships in a fleet with their modules"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT id, fleet_id, ship_class, project, callsign, current_crew, 
                   required_crew, status, created_at FROM ships WHERE fleet_id = ?""",
                (fleet_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                ships = []
                for row in rows:
                    ship_dict = dict(row)
                    # Get modules for this ship
                    modules_data = await self.get_ship_modules(row['id'])
                    ship_modules = []
                    for mod_data in modules_data:
                        module = Module(
                            id=mod_data['module_id'],
                            name=mod_data['name'],
                            type=mod_data['type'],
                            weight=mod_data['weight'],
                            price=mod_data['price'],
                            stats=json.loads(mod_data['stats']) if isinstance(mod_data['stats'], str) else mod_data['stats']
                        )
                        ship_modules.append(ShipModule(
                            id=mod_data['id'],
                            ship_id=row['id'],
                            module_id=mod_data['module_id'],
                            count=mod_data['count'],
                            module=module
                        ))
                    ship_dict['modules'] = ship_modules
                    # Parse datetime if present
                    if ship_dict.get('created_at'):
                        ship_dict['created_at'] = parse_datetime(ship_dict['created_at'])
                    ships.append(Ship(**ship_dict))
                return ships

    async def remove_ship(self, ship_id: int) -> None:
        """Remove a ship and its modules"""
        async with aiosqlite.connect(self.db_path) as db:
            # Remove ship modules first
            await db.execute("DELETE FROM ship_modules WHERE ship_id = ?", (ship_id,))
            # Remove ship
            await db.execute("DELETE FROM ships WHERE id = ?", (ship_id,))
            await db.commit()

    async def update_fleet_resources(self, fleet_id: int, **kwargs) -> None:
        """Update fleet resources"""
        if not kwargs:
            return
        async with aiosqlite.connect(self.db_path) as db:
            update_fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            update_fields += ", updated_at = CURRENT_TIMESTAMP"
            values = list(kwargs.values()) + [fleet_id]
            await db.execute(
                f"UPDATE fleets SET {update_fields} WHERE id = ?",
                values
            )
            await db.commit()

    async def increment_turn(self, fleet_id: int, salary: int, rations_needed: int) -> None:
        """Increment turn count and deduct resources"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE fleets 
                   SET turn_count = turn_count + 1,
                       gold = gold - ?,
                       rations = rations - ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (salary, rations_needed, fleet_id)
            )
            await db.commit()

    async def get_inventory(self, fleet_id: int) -> List[Dict[str, Any]]:
        """Get fleet inventory"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT fi.id, fi.fleet_id, fi.module_id, fi.count,
                   m.id as module_id, m.name, m.type, m.weight, m.price, m.stats
                   FROM fleet_inventory fi
                   JOIN modules m ON fi.module_id = m.id
                   WHERE fi.fleet_id = ?""",
                (fleet_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                result = []
                for row in rows:
                    result.append({
                        'id': row['id'],
                        'fleet_id': row['fleet_id'],
                        'module_id': row['module_id'],
                        'count': row['count'],
                        'module': {
                            'id': row['module_id'],
                            'name': row['name'],
                            'type': row['type'],
                            'weight': row['weight'],
                            'price': row['price'],
                            'stats': json.loads(row['stats']) if isinstance(row['stats'], str) else row['stats']
                        }
                    })
                return result

    async def add_module_to_inventory(self, fleet_id: int, module_id: int, count: int = 1) -> None:
        """Add module to fleet inventory"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if already exists
            async with db.execute(
                "SELECT count FROM fleet_inventory WHERE fleet_id = ? AND module_id = ?",
                (fleet_id, module_id)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    # Update count
                    await db.execute(
                        "UPDATE fleet_inventory SET count = count + ? WHERE fleet_id = ? AND module_id = ?",
                        (count, fleet_id, module_id)
                    )
                else:
                    # Insert new
                    await db.execute(
                        "INSERT INTO fleet_inventory (fleet_id, module_id, count) VALUES (?, ?, ?)",
                        (fleet_id, module_id, count)
                    )
            await db.commit()

    async def remove_module_from_inventory(self, fleet_id: int, module_id: int, count: int = 1) -> bool:
        """Remove module from fleet inventory"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check current count
            async with db.execute(
                "SELECT count FROM fleet_inventory WHERE fleet_id = ? AND module_id = ?",
                (fleet_id, module_id)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                
                current_count = row['count']
                if current_count < count:
                    return False
                
                if current_count == count:
                    # Remove entirely
                    await db.execute(
                        "DELETE FROM fleet_inventory WHERE fleet_id = ? AND module_id = ?",
                        (fleet_id, module_id)
                    )
                else:
                    # Decrease count
                    await db.execute(
                        "UPDATE fleet_inventory SET count = count - ? WHERE fleet_id = ? AND module_id = ?",
                        (count, fleet_id, module_id)
                    )
                await db.commit()
                return True

    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            logger.info("Database connection closed")
