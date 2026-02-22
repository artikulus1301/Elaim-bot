import discord
from discord.ext import commands
from utils.constants import SHIP_SPECS, ShipClass
from utils.helpers import format_currency, format_number, calculate_methane_consumption

class Calculator(commands.Cog):
    """Калькуляторы ресурсов для Highfleet"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="расчет", aliases=["calc", "calculate"])
    async def calculate_ship(self, ctx, ship_type: str, crew: int = None, distance: int = 100):
        """
        Расчет потребления ресурсов для корабля
        Использование: !расчет [тип_корабля] [экипаж] [расстояние_км]
        Пример: !расчет корвет 50 100
        """
        ship_class = None
        ship_key = ship_type.lower()
        
        # Определяем класс корабля
        for enum_member in ShipClass:
            if ship_key in enum_member.value or ship_key in str(enum_member.value):
                ship_class = enum_member
                break
        
        if not ship_class and "корвет" in ship_key:
            ship_class = ShipClass.STRIKE_CORVETTE
        elif not ship_class and "фрегат" in ship_key:
            ship_class = ShipClass.ARTILLERY_FRIGATE
        elif not ship_class and "крейсер" in ship_key:
            ship_class = ShipClass.HEAVY_CRUISER
        
        if not ship_class:
            await ctx.send("❌ Неизвестный тип корабля. Доступные: корвет, фрегат, крейсер")
            return
        
        specs = SHIP_SPECS[ship_class]
        actual_crew = crew if crew else specs[1]
        
        # Расчеты
        salary = actual_crew * 2  # 2 ЗР за ход
        rations = actual_crew * 1  # 1 паек за ход
        methane = calculate_methane_consumption(ship_class, distance)
        
        embed = discord.Embed(
            title=f"📊 Расчет ресурсов: {ship_class.value.replace('_', ' ').title()}",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="⚙️ Характеристики",
            value=f"Тип: **{specs[0].value.title()}**\n"
                  f"Требуемый экипаж: **{specs[1]}** чел.\n"
                  f"Базовая цена: **{format_currency(specs[3])}**",
            inline=False
        )
        
        embed.add_field(
            name="💰 Расходы за ход",
            value=f"Жалование: **{format_currency(salary)}**\n"
                  f"Пайки: **{format_number(rations)}** шт.",
            inline=False
        )
        
        embed.add_field(
            name="⛽ Топливо",
            value=f"Расход на {distance} км: **{format_number(methane)}** тонн метана\n"
                  f"(Базовый расход: {specs[2]} тонн/100км)",
            inline=False
        )
        
        if crew and crew != specs[1]:
            efficiency = (crew / specs[1]) * 100
            embed.add_field(
                name="⚠️ Внимание",
                value=f"Экипаж неполный ({efficiency:.0f}% эффективности)\n"
                      f"Рекомендуется: {specs[1]} человек",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="метан", aliases=["fuel", "топливо"])
    async def calculate_fuel(self, ctx, ship_type: str, distance: int):
        """Расчет потребления метана на расстояние"""
        await self.calculate_ship(ctx, ship_type, distance=distance)
    
    @commands.command(name="флот_расчет", aliases=["fleet_calc"])
    async def calculate_fleet_consumption(self, ctx):
        """Расчет потребления всего флота игрока"""
        db = self.bot.db
        fleet = await db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        
        if not fleet:
            await ctx.send("❌ У вас нет зарегистрированной флотилии. Используйте `!анкета`")
            return
        
        fleet_full = await db.get_fleet_with_ships(fleet.id)
        
        embed = discord.Embed(
            title=f"📊 Расчет флотилии: {fleet_full.name}",
            color=0xe74c3c
        )
        
        # Общие расходы
        embed.add_field(
            name="💰 Ежеходовые расходы",
            value=f"Жалование: **{format_currency(fleet_full.salary_per_turn)}**\n"
                  f"Пайки: **{format_number(fleet_full.rations_per_turn)}** шт.\n"
                  f"Всего экипажа: **{fleet_full.total_crew}** / {fleet_full.required_crew}",
            inline=False
        )
        
        # Расход метана
        methane_100 = fleet_full.methane_per_100km
        embed.add_field(
            name="⛽ Расход метана",
            value=f"На 100 км: **{format_number(methane_100)}** тонн\n"
                  f"На 500 км: **{format_number(methane_100 * 5)}** тонн\n"
                  f"На 1000 км: **{format_number(methane_100 * 10)}** тонн",
            inline=False
        )
        
        # Достаточность ресурсов
        turns_gold = fleet_full.gold // fleet_full.salary_per_turn if fleet_full.salary_per_turn > 0 else float('inf')
        turns_rations = fleet_full.rations // fleet_full.rations_per_turn if fleet_full.rations_per_turn > 0 else float('inf')
        methane_100 = fleet_full.methane_per_100km
        
        embed.add_field(
            name="⏳ Ходов до истощения",
            value=f"💰 Золота хватит на: **{turns_gold:.0f}** ходов\n"
                  f"🍞 Пайков хватит на: **{turns_rations:.0f}** ходов\n"
                  f"⛽ Метана хватит на: **{fleet_full.methane // methane_100 if methane_100 > 0 else 0:.0f}** единиц по 100км",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Calculator(bot))
