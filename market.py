import discord
from discord.ext import commands
from models.database import Database
from models.schemas import ModuleType
from utils.helpers import format_currency
from utils.game_mechanics import MODULE_PROTOTYPES, seed_modules

class Market(commands.Cog):
    """Рынок, инвентарь и перемещение"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db: Database = bot.db
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Seed modules on startup"""
        await seed_modules(self.db)

    # --- INVENTORY ---

    @commands.command(name="склад", aliases=["inventory", "inv"])
    async def show_inventory(self, ctx):
        """Показать содержимое склада"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии.")
            return

        items = await self.db.get_inventory(fleet.id)
        
        if not items:
            await ctx.send("📦 Ваш склад пуст.")
            return

        embed = discord.Embed(title=f"📦 Склад флотилии {fleet.name}", color=0x9b59b6)
        
        text = ""
        for item in items:
            module = item['module']
            text += f"**{module['name']}** (x{item['count']})\n"
            text += f"└ Тип: {module['type']} | Вес: {module['weight']}т | Цена: {format_currency(module['price'])}\n\n"
        
        embed.description = text
        await ctx.send(embed=embed)

    # --- SHOP & MOVEMENT ---

    @commands.command(name="перелет", aliases=["travel", "move"])
    @commands.has_permissions(administrator=True) # Admin only as requested
    async def admin_move_fleet(self, ctx, member: discord.Member, distance: int, location_name: str, *, spec: str):
        """
        [АДМИН] Переместить флот игрока
        !перелет @игрок [расстояние] "Название" [Специализация]
        Пример: !перелет @User 300 "Кушан" Топливохранилище
        """
        fleet = await self.db.get_fleet_by_user(member.id, ctx.guild.id)
        if not fleet:
            await ctx.send(f"❌ У {member.mention} нет флотилии.")
            return
            
        # Parse specialization from string if needed, or take as raw text
        # Valid specs: База Флота, Наемники, Торговцы, Верфи, Топливохранилище, Узел Связи
        
        await self.db.update_fleet_location(fleet.id, location_name, spec)
        
        # Consume fuel? 
        # Logic: 100km = specific methane. 
        # Calculate cost
        
        fleet_full = await self.db.get_fleet_with_ships(fleet.id)
        methane_cost = int((fleet_full.methane_per_100km / 100) * distance)
        
        # Deduct fuel
        new_methane = max(0, fleet.methane - methane_cost)
        await self.db.update_fleet_resources(fleet.id, methane=new_methane)
        
        await ctx.send(
            f"🚀 **Перелет завершен**\n"
            f"Флот: {fleet.name}\n"
            f"Новая локация: {location_name} ({spec})\n"
            f"Потрачено топлива: {methane_cost} тонн (Ост: {new_methane})"
        )

    @commands.command(name="магазин", aliases=["shop", "store"])
    async def show_shop(self, ctx):
        """
        Показать доступные товары в текущей локации
        Скидки и ассортимент зависят от специализации города
        """
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии.")
            return
            
        spec = fleet.location_spec.lower()
        discount = 1.0
        available_types = []
        
        # Logic for specs
        if "база флота" in spec:
            discount = 0.7 # 30% discount
            available_types = [ModuleType.WEAPON, ModuleType.AMMO, ModuleType.FUEL_TANK, ModuleType.HULL, ModuleType.ARMOR, ModuleType.ENGINE]
        elif "торговцы" in spec:
            available_types = [t for t in ModuleType] # All
        elif "топливохранилище" in spec:
            available_types = [ModuleType.FUEL_TANK]
        else:
             available_types = [ModuleType.ARMOR, ModuleType.FUEL_TANK]

        # RESOURCE PRICES (Base)
        rations_price = 10
        methane_price = 5

        # Fuel Depot discount for Methane
        methane_discount = 0.5 if "топливохранилище" in spec else 1.0
        
        embed = discord.Embed(
            title=f"🏪 Магазин - {fleet.location}",
            description=f"Специализация: **{fleet.location_spec}**\nСкидка: **{int((1-discount)*100)}%**",
            color=0xf1c40f
        )
        
        # Resources Section
        res_text = (
            f"🍞 **Пайки** (`rations`)\nЦена: {format_currency(int(rations_price * discount))}\n"
            f"⛽ **Метан** (`methane`)\nЦена: {format_currency(int(methane_price * methane_discount))}"
        )
        embed.add_field(name="📦 Ресурсы", value=res_text, inline=False)

        # Modules Section
        all_modules = await self.db.get_all_modules()
        for mod in all_modules:
            if mod['type'] in available_types or "торговцы" in spec or "база" in spec:
                price = int(mod['price'] * discount)
                embed.add_field(
                    name=f"{mod['name']} (ID: {mod['id']})",
                    value=f"Цена: {format_currency(price)}\nВес: {mod['weight']}т",
                    inline=True
                )
                
        embed.set_footer(text="Купить: !купить [ID или rations/methane] [Кол-во]")
        await ctx.send(embed=embed)

    @commands.command(name="купить", aliases=["buy"])
    async def buy_item(self, ctx, item_identifier: str, amount: int = 1):
        """
        Купить предмет или ресурс
        Использование: !купить [ID или rations/methane] [количество]
        Пример: !купить rations 100
        Пример: !купить 5 1
        """
        if amount <= 0:
            await ctx.send("❌ Количество должно быть положительным.")
            return

        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии.")
            return
            
        spec = fleet.location_spec.lower()
        discount = 0.7 if "база флота" in spec else 1.0

        # --- RESOURCE PURCHASE ---
        if item_identifier.lower() in ["rations", "пайки", "провиант"]:
            base_price = 10
            price = int(base_price * discount) * amount
            
            if fleet.gold < price:
                await ctx.send(f"❌ Недостаточно средств! Нужно {format_currency(price)}")
                return
            
            await self.db.update_fleet_resources(fleet.id, gold=fleet.gold - price, rations=fleet.rations + amount)
            await ctx.send(f"✅ Куплено: **Пайки** x{amount} за {format_currency(price)}")
            return

        if item_identifier.lower() in ["methane", "метан", "топливо", "fuel"]:
            base_price = 5
            # Fuel Depot special discount
            fuel_discount = 0.5 if "топливохранилище" in spec else 1.0
            price = int(base_price * fuel_discount) * amount
            
            if fleet.gold < price:
                await ctx.send(f"❌ Недостаточно средств! Нужно {format_currency(price)}")
                return
                
            await self.db.update_fleet_resources(fleet.id, gold=fleet.gold - price, methane=fleet.methane + amount)
            await ctx.send(f"✅ Куплено: **Метан** {amount} тонн за {format_currency(price)}")
            return

        # --- MODULE PURCHASE ---
        if not item_identifier.isdigit():
            await ctx.send("❌ Неверный ID предмета или название ресурса. Используйте ID для модулей или 'rations'/'methane' для ресурсов.")
            return
            
        item_id = int(item_identifier)
        module = await self.db.get_module(item_id)
        if not module:
            await ctx.send("❌ Предмет не найден.")
            return
            
        total_price = int(module['price'] * discount * amount)
        
        if fleet.gold < total_price:
            await ctx.send(f"❌ Недостаточно средств! Нужно {format_currency(total_price)}")
            return
            
        # Transaction
        await self.db.update_fleet_resources(fleet.id, gold=fleet.gold - total_price)
        await self.db.add_module_to_inventory(fleet.id, item_id, amount)
        
        await ctx.send(f"✅ Куплено: {module['name']} x{amount} за {format_currency(total_price)}")

    @commands.command(name="продать", aliases=["sell"])
    async def sell_item(self, ctx, item_id: int, amount: int = 1):
        """Продать предмет из инвентаря (50% от стоимости)"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet: return
        
        module = await self.db.get_module(item_id)
        if not module: return
        
        success = await self.db.remove_module_from_inventory(fleet.id, item_id, amount)
        if not success:
            await ctx.send("❌ Недостаточно предметов на складе.")
            return
            
        sell_price = int(module['price'] * 0.5 * amount)
        await self.db.update_fleet_resources(fleet.id, gold=fleet.gold + sell_price)
        
        await ctx.send(f"✅ Продано: {module['name']} x{amount} за {format_currency(sell_price)}")

    # --- OUTFITTING ---

    @commands.command(name="оснастить", aliases=["equip", "fit"])
    async def equip_ship(self, ctx, callsign: str, module_id: int):
        """Установить модуль со склада на корабль"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet: return
        
        # 1. Check ship
        ships = await self.db.get_ships_by_fleet(fleet.id)
        target_ship = next((s for s in ships if s.callsign.lower() == callsign.lower()), None)
        if not target_ship:
            await ctx.send(f"❌ Корабль '{callsign}' не найден.")
            return

        # 2. Check module in inventory
        inv = await self.db.get_inventory(fleet.id)
        inv_item = next((i for i in inv if i['module_id'] == module_id), None)
        if not inv_item or inv_item['count'] < 1:
            await ctx.send("❌ Модуль отсутствует на складе.")
            return

        # 3. Check flight capabilities (Thrust vs Weight) logic
        # Ideally we check PREDICTION here. 
        # Get module stats
        module = inv_item['module']
        
        # Create temp ship object or just calc manually?
        # Let's fetch current modules
        current_modules = await self.db.get_ship_modules(target_ship.id)
        
        # Calc current weight/thrust
        # Calc current weight/thrust
        curr_weight = sum(m['weight'] * m['count'] for m in current_modules)
        curr_thrust = sum(m['module']['stats'].get('thrust', 0) * m['count'] for m in current_modules if m['type'] == 'двигатель')
        
        new_weight = curr_weight + module['weight']
        new_thrust = curr_thrust + module['stats'].get('thrust', 0) if module['type'] == 'двигатель' else curr_thrust
        
        if new_weight > new_thrust:
            await ctx.send(f"⚠️ **Внимание:** Корабль будет перегружен! (Тяга {new_thrust} < Вес {new_weight})\nМодуль все равно установлен.")
        
        # 4. Move item
        await self.db.remove_module_from_inventory(fleet.id, module_id, 1)
        await self.db.add_module_to_ship(target_ship.id, module_id, 1)
        
        await ctx.send(f"✅ Модуль **{module['name']}** установлен на **{target_ship.callsign}**")

    @commands.command(name="снять", aliases=["unequip", "strip"])
    async def unequip_ship(self, ctx, callsign: str, module_id: int):
        """Снять модуль с корабля на склад"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet: return

        ships = await self.db.get_ships_by_fleet(fleet.id)
        target_ship = next((s for s in ships if s.callsign.lower() == callsign.lower()), None)
        if not target_ship:
            await ctx.send(f"❌ Корабль '{callsign}' не найден.")
            return
            
        # Check module on ship
        await self.db.remove_module_from_ship(target_ship.id, module_id, 1)
        await self.db.add_module_to_inventory(fleet.id, module_id, 1)
        
        await ctx.send(f"✅ Модуль снят и отправлен на склад.")

async def setup(bot):
    await bot.add_cog(Market(bot))