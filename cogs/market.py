import discord
from discord.ext import commands
from models.database import Database
from models.schemas import ModuleType
from utils.helpers import format_currency
from utils.game_mechanics import MODULE_PROTOTYPES, seed_modules

class ShopView(discord.ui.View):
    def __init__(self, items, fleet, discount, methane_discount, items_per_page=8):
        super().__init__(timeout=60)
        self.items = items
        self.fleet = fleet
        self.discount = discount
        self.methane_discount = methane_discount
        self.items_per_page = items_per_page
        self.current_page = 0
        self.total_pages = (len(items) - 1) // items_per_page + 1 if items else 1

    def create_embed(self):
        embed = discord.Embed(
            title=f"🏪 Магазин - {self.fleet.location}",
            description=f"Специализация: **{self.fleet.location_spec}**\nСкидка: **{int((1-self.discount)*100)}%**\nСтраница {self.current_page + 1}/{self.total_pages}",
            color=0xf1c40f
        )
        
        # Resources (always on first page)
        if self.current_page == 0:
            rations_price = 10
            methane_price = 5
            res_text = (
                f"🍞 **Пайки** (`rations`)\nЦена: {format_currency(int(rations_price * self.discount))}\n"
                f"⛽ **Метан** (`methane`)\nЦена: {format_currency(int(methane_price * self.methane_discount))}"
            )
            embed.add_field(name="📦 Ресурсы", value=res_text, inline=False)

        # Modules
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = self.items[start:end]

        for mod in page_items:
            price = int(mod['price'] * self.discount)
            embed.add_field(
                name=f"{mod['name']} (ID: {mod['id']})",
                value=f"Цена: {format_currency(price)}\nВес: {mod['weight']}т",
                inline=True
            )
            
        embed.set_footer(text="Купить: !купить [ID или rations/methane] [Кол-во]")
        return embed

    @discord.ui.button(label="◀️ Назад", style=discord.ButtonStyle.gray)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Вперед ▶️", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

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
            
        await self.db.update_fleet_location(fleet.id, location_name, spec)
        
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
        discount = 0.7 if "база флота" in spec else 1.0
        methane_discount = 0.5 if "топливохранилище" in spec else 1.0
        
        available_types = []
        if "база флота" in spec:
             available_types = [ModuleType.WEAPON, ModuleType.AMMO, ModuleType.FUEL_TANK, ModuleType.HULL, ModuleType.ARMOR, ModuleType.ENGINE]
        elif "торговцы" in spec:
            available_types = [t for t in ModuleType]
        elif "топливохранилище" in spec:
            available_types = [ModuleType.FUEL_TANK]
        else:
             available_types = [ModuleType.ARMOR, ModuleType.FUEL_TANK]

        all_modules = await self.db.get_all_modules()
        shop_modules = [m for m in all_modules if m['type'] in available_types or "торговцы" in spec or "база" in spec]
        
        view = ShopView(shop_modules, fleet, discount, methane_discount)
        await ctx.send(embed=view.create_embed(), view=view)

    @commands.command(name="купить", aliases=["buy"])
    async def buy_item(self, ctx, item_identifier: str, amount: int = 1):
        """
        Купить предмет или ресурс
        Использование: !купить [ID или rations/methane] [количество]
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

        if item_identifier.lower() in ["rations", "пайки", "провиант"]:
            price = int(10 * discount) * amount
            if fleet.gold < price:
                await ctx.send(f"❌ Недостаточно средств! Нужно {format_currency(price)}")
                return
            await self.db.update_fleet_resources(fleet.id, gold=fleet.gold - price, rations=fleet.rations + amount)
            await ctx.send(f"✅ Куплено: **Пайки** x{amount} за {format_currency(price)}")
            return

        if item_identifier.lower() in ["methane", "метан", "топливо", "fuel"]:
            fuel_discount = 0.5 if "топливохранилище" in spec else 1.0
            price = int(5 * fuel_discount) * amount
            if fleet.gold < price:
                await ctx.send(f"❌ Недостаточно средств! Нужно {format_currency(price)}")
                return
            await self.db.update_fleet_resources(fleet.id, gold=fleet.gold - price, methane=fleet.methane + amount)
            await ctx.send(f"✅ Куплено: **Метан** {amount} тонн за {format_currency(price)}")
            return

        if not item_identifier.isdigit():
            await ctx.send("❌ Неверный ID модуля или название ресурса.")
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
            
        await self.db.update_fleet_resources(fleet.id, gold=fleet.gold - total_price)
        await self.db.add_module_to_inventory(fleet.id, item_id, amount)
        await ctx.send(f"✅ Куплено: {module['name']} x{amount} за {format_currency(total_price)}")

    @commands.command(name="продать", aliases=["sell"])
    async def sell_item(self, ctx, item_id: int, amount: int = 1):
        """Продать предмет из инвентаря (50% от стоимости)"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии.")
            return
        
        module = await self.db.get_module(item_id)
        if not module:
            await ctx.send(f"❌ Модуль с ID {item_id} не существует.")
            return
        
        success = await self.db.remove_module_from_inventory(fleet.id, item_id, amount)
        if not success:
            await ctx.send("❌ Недостаточно предметов на складе.")
            return
            
        sell_price = int(module['price'] * 0.5 * amount)
        await self.db.update_fleet_resources(fleet.id, gold=fleet.gold + sell_price)
        await ctx.send(f"✅ Продано: {module['name']} x{amount} за {format_currency(sell_price)}")

    @commands.command(name="оснастить", aliases=["equip", "fit"])
    async def equip_ship(self, ctx, callsign: str, module_id: int):
        """Установить модуль со склада на корабль"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии.")
            return
        
        ships = await self.db.get_ships_by_fleet(fleet.id)
        target_ship = next((s for s in ships if s.callsign.lower() == callsign.lower()), None)
        if not target_ship:
            await ctx.send(f"❌ Корабль '{callsign}' не найден.")
            return

        inv = await self.db.get_inventory(fleet.id)
        inv_item = next((i for i in inv if i['module_id'] == module_id), None)
        if not inv_item or inv_item['count'] < 1:
            await ctx.send("❌ Модуль отсутствует на складе.")
            return

        module = inv_item['module']
        current_modules = await self.db.get_ship_modules(target_ship.id)
        
        curr_weight = sum(m['weight'] * m['count'] for m in current_modules)
        curr_thrust = sum(m['module']['stats'].get('thrust', 0) * m['count'] for m in current_modules if m['type'] == 'двигатель')
        
        new_weight = curr_weight + module['weight']
        new_thrust = curr_thrust + module['stats'].get('thrust', 0) if module['type'] == 'двигатель' else curr_thrust
        
        if new_weight > new_thrust:
            await ctx.send(f"⚠️ **Внимание:** Корабль перегружен! (Тяга {new_thrust} < Вес {new_weight})")
        
        await self.db.remove_module_from_inventory(fleet.id, module_id, 1)
        await self.db.add_module_to_ship(target_ship.id, module_id, 1)
        await ctx.send(f"✅ Модуль **{module['name']}** установлен на **{target_ship.callsign}**")

    @commands.command(name="снять", aliases=["unequip", "strip"])
    async def unequip_ship(self, ctx, callsign: str, module_id: int):
        """Снять модуль с корабля на склад"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии.")
            return

        ships = await self.db.get_ships_by_fleet(fleet.id)
        target_ship = next((s for s in ships if s.callsign.lower() == callsign.lower()), None)
        if not target_ship:
            await ctx.send(f"❌ Корабль '{callsign}' не найден.")
            return
            
        success = await self.db.remove_module_from_ship(target_ship.id, module_id, 1)
        if not success:
            await ctx.send("❌ Этот модуль не установлен на корабле.")
            return

        await self.db.add_module_to_inventory(fleet.id, module_id, 1)
        await ctx.send(f"✅ Модуль снят и отправлен на склад.")

async def setup(bot):
    await bot.add_cog(Market(bot))