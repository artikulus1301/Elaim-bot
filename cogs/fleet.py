import discord
from discord.ext import commands
from models.database import Database
from models.schemas import ShipStatus
from utils.helpers import parse_ship_input, format_currency

class FleetManager(commands.Cog):
    """Управление флотом игрока"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db: Database = bot.db
    
    @commands.command(name="анкета", aliases=["регистрация", "start"])
    async def register_fleet(self, ctx):
        """
        Регистрация новой флотилии
        Запускает диалог сбора информации
        """
        # Проверяем, есть ли уже флот
        existing = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if existing:
            await ctx.send(f"❌ У вас уже есть флотилия **{existing.name}**. Используйте `!флот` для просмотра.")
            return
        
        await ctx.send("⚓ **Регистрация новой флотилии**\nВведите название вашей флотилии:")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            # Название флотилии
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            fleet_name = msg.content.strip()
            
            if len(fleet_name) < 2 or len(fleet_name) > 100:
                await ctx.send("❌ Название должно быть от 2 до 100 символов.")
                return
            
            await ctx.send("👤 Введите имя Тархана (командира флотилии):")
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            leader_name = msg.content.strip()
            
            if len(leader_name) < 2 or len(leader_name) > 50:
                await ctx.send("❌ Имя должно быть от 2 до 50 символов.")
                return
            
            # Создаем флот
            fleet = await self.db.create_fleet(
                user_id=ctx.author.id,
                guild_id=ctx.guild.id,
                name=fleet_name,
                leader_name=leader_name
            )
            
            # Начальные ресурсы
            await self.db.update_fleet_resources(fleet.id, rations=100, methane=200)
            
            embed = discord.Embed(
                title="✅ Флотилия зарегистрирована!",
                description=f"**{fleet_name}**\nТархан: {leader_name}",
                color=0x2ecc71
            )
            embed.add_field(
                name="💰 Стартовый капитал",
                value=f"{format_currency(fleet.gold)}\n100 пайков\n200 тонн метана",
                inline=False
            )
            embed.add_field(
                name="📝 Следующие шаги",
                value="Используйте `!добавить_корабль` чтобы добавить корабли во флот\n"
                      "Используйте `!флот` чтобы посмотреть статус",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except TimeoutError:
            await ctx.send("⏰ Время ожидания истекло. Попробуйте снова.")
    
    @commands.command(name="флот", aliases=["fleet", "таблица"])
    async def show_fleet(self, ctx, member: discord.Member = None):
        """
        Показать таблицу флота игрока
        Можно указать @упоминание чтобы посмотреть чужой флот
        """
        target_user = member or ctx.author
        fleet = await self.db.get_fleet_by_user(target_user.id, ctx.guild.id)
        
        if not fleet:
            if member:
                await ctx.send(f"❌ У {target_user.mention} нет зарегистрированной флотилии.")
            else:
                await ctx.send("❌ У вас нет флотилии. Используйте `!анкета` для регистрации.")
            return
        
        fleet_full = await self.db.get_fleet_with_ships(fleet.id)
        embed_data = fleet_full.to_discord_embed()
        
        embed = discord.Embed.from_dict(embed_data)
        await ctx.send(embed=embed)
    
    @commands.command(name="добавить_корабль", aliases=["add_ship", "новый_корабль"])
    async def add_ship(self, ctx, *, ship_data: str = None):
        """Добавить корабль во флот (упрощенный или полный формат)"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ Сначала зарегистрируйте флотилию командой `!анкета`")
            return
        
        if not ship_data:
            await ctx.send(
                "🚀 **Добавление корабля**\n"
                "Введите данные в одном из форматов:\n"
                "1. `!добавить_корабль [Проект] [Позывной]`\n"
                "   *Пример: `!добавить_корабль Севастополь Призрак`*\n\n"
                "2. `!добавить_корабль [Тип] пр-к [Проект] - [Позывной]`\n"
                "   *Пример: `!добавить_корабль Ударный Корвет пр-к Молния - Находчивый`*\n\n"
                "**Доступные проекты:** " + ", ".join(list(self.get_available_projects()))
            )
            return

        parsed = parse_ship_input(ship_data)
        
        if not parsed:
            await ctx.send(
                "❌ Не удалось распознать формат.\n"
                "Попробуйте: `!добавить_корабль Севастополь Призрак`"
            )
            return
        
        # Создаем корабль
        ship = await self.db.add_ship(
            fleet_id=fleet.id,
            ship_class=parsed['ship_class'].value,
            project=parsed['project'],
            callsign=parsed['callsign'],
            current_crew=parsed['current_crew'],
            required_crew=parsed['required_crew'],
            status=parsed['status']
        )
        
        # Добавляем базовые модули
        await self.equip_default_modules(ship)
        
        # Получаем обновленный корабль с модулями для вывода
        ship = await self.db.get_ship(ship.id)
        
        embed = discord.Embed(
            title="✅ Корабль добавлен и оснащен!",
            color=0x2ecc71
        )
        embed.add_field(name="Позывной", value=f"**{ship.callsign}**", inline=True)
        embed.add_field(name="Проект", value=ship.project, inline=True)
        embed.add_field(name="Класс", value=ship.ship_class.replace('_', ' ').title(), inline=True)
        embed.add_field(name="Экипаж", value=f"{ship.current_crew}/{ship.required_crew}", inline=True)
        
        if ship.modules:
            mods_list = "\n".join([f"• {m.module.name} x{m.count}" for m in ship.modules if m.module])
            embed.add_field(name="Установленное оборудование", value=mods_list, inline=False)
            
        await ctx.send(embed=embed)

    def get_available_projects(self):
        from utils.ship_presets import SHIP_PRESETS
        return [p.capitalize() for p in SHIP_PRESETS.keys()]

    async def equip_default_modules(self, ship):
        """Устанавливает базовые модули из пресетов"""
        from utils.ship_presets import SHIP_PRESETS
        
        project_key = ship.project.lower()
        if project_key not in SHIP_PRESETS:
            return

        preset = SHIP_PRESETS[project_key]
        all_modules = await self.db.get_all_modules()
        
        def find_id(name_part):
            for m in all_modules:
                if name_part.lower() in m['name'].lower():
                    return m['id']
            return None

        for mod_name, count in preset["loadout"]:
            mod_id = find_id(mod_name)
            if mod_id:
                try:
                    await self.db.add_module_to_ship(ship.id, mod_id, count)
                except Exception as e:
                    print(f"Error adding module {mod_name}: {e}")
    
    @commands.command(name="корабль", aliases=["ship", "stats", "статистика"])
    async def show_ship_stats(self, ctx, *, callsign: str):
        """Показать подробную статистику корабля"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии.")
            return

        ships = await self.db.get_ships_by_fleet(fleet.id)
        target_ship = next((s for s in ships if s.callsign.lower() == callsign.lower()), None)
        
        if not target_ship:
            await ctx.send(f"❌ Корабль '{callsign}' не найден.")
            return
            
        # Загружаем модули
        from models.schemas import ShipModule
        modules_data = await self.db.get_ship_modules(target_ship.id)
        target_ship.modules = [ShipModule(**m) for m in modules_data]
        
        # Расчеты
        total_hp = target_ship.total_hp
        weight = target_ship.total_weight
        thrust = target_ship.total_thrust
        twr = thrust / weight if weight > 0 else 0
        evasion = target_ship.evasion
        
        embed = discord.Embed(
            title=f"🚀 {target_ship.callsign}",
            description=f"**{target_ship.ship_class.replace('_', ' ').title()}** (Проект: {target_ship.project})",
            color=0x3498db
        )
        
        # Основные статы
        stats_text = (
            f"❤️ Прочность: **{total_hp}**\n"
            f"⚖️ Вес: **{weight}т**\n"
            f"💨 Тяга: **{thrust}т** (TWR: {twr:.2f})\n"
            f"⚡ Уклонение: **{int(evasion*100)}%**\n"
            f"👥 Экипаж: **{target_ship.current_crew}/{target_ship.required_crew}**"
        )
        embed.add_field(name="📊 Характеристики", value=stats_text, inline=False)
        
        # Модули
        modules_text = ""
        if target_ship.modules:
            for sm in target_ship.modules:
                if sm.module:
                    modules_text += f"• **{sm.module.name}** x{sm.count}\n"
        else:
            modules_text = "*Нет установленных модулей*"
            
        embed.add_field(name="🛠️ Оснащение", value=modules_text, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="удалить_корабль", aliases=["remove_ship"])
    async def remove_ship(self, ctx, *, callsign: str):
        """Удалить корабль по позывному"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии.")
            return
        
        ships = await self.db.get_ships_by_fleet(fleet.id)
        target_ship = None
        
        for ship in ships:
            if ship.callsign.lower() == callsign.lower():
                target_ship = ship
                break
        
        if not target_ship:
            await ctx.send(f"❌ Корабль с позывным \"{callsign}\" не найден.")
            return
        
        await self.db.remove_ship(target_ship.id)
        await ctx.send(f"✅ Корабль \"{callsign}\" удален из флотилии.")
    
    @commands.command(name="обновить_экипаж", aliases=["crew", "экипаж"])
    async def update_crew(self, ctx, callsign: str, new_crew: int):
        """Обновить количество экипажа на корабле"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии.")
            return
        
        ships = await self.db.get_ships_by_fleet(fleet.id)
        target_ship = None
        
        for ship in ships:
            if ship.callsign.lower() == callsign.lower():
                target_ship = ship
                break
        
        if not target_ship:
            await ctx.send(f"❌ Корабль с позывным \"{callsign}\" не найден.")
            return
        
        if new_crew < 0 or new_crew > target_ship.required_crew * 2:
            await ctx.send(f"❌ Некорректное количество экипажа (0-{target_ship.required_crew * 2}).")
            return
        
        await self.db.update_ship_crew(target_ship.id, new_crew)
        await ctx.send(
            f"✅ Экипаж корабля \"{callsign}\" обновлен: {new_crew}/{target_ship.required_crew}"
        )
    
    @commands.command(name="статус", aliases=["повреждения", "damage"])
    async def update_status(self, ctx, callsign: str, *, new_status: str):
        """Обновить статус повреждений корабля"""
        fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        if not fleet:
            await ctx.send("❌ У вас нет флотилии.")
            return
        
        # Нормализуем статус
        status_map = {
            "в строю": ShipStatus.OPERATIONAL,
            "строю": ShipStatus.OPERATIONAL,
            "боеготов": ShipStatus.OPERATIONAL,
            "легкие": ShipStatus.LIGHT_DAMAGE,
            "легкие повреждения": ShipStatus.LIGHT_DAMAGE,
            "средние": ShipStatus.MODERATE_DAMAGE,
            "средние повреждения": ShipStatus.MODERATE_DAMAGE,
            "тяжелые": ShipStatus.HEAVY_DAMAGE,
            "тяжелые повреждения": ShipStatus.HEAVY_DAMAGE,
            "критические": ShipStatus.CRITICAL_DAMAGE,
            "крит": ShipStatus.CRITICAL_DAMAGE,
            "уничтожен": ShipStatus.DESTROYED,
            "мертв": ShipStatus.DESTROYED,
        }
        
        status_key = new_status.lower().strip()
        status = status_map.get(status_key)
        
        if not status:
            available = ", ".join([s.value for s in ShipStatus])
            await ctx.send(f"❌ Неизвестный статус. Доступные: {available}")
            return
        
        ships = await self.db.get_ships_by_fleet(fleet.id)
        target_ship = None
        
        for ship in ships:
            if ship.callsign.lower() == callsign.lower():
                target_ship = ship
                break
        
        if not target_ship:
            await ctx.send(f"❌ Корабль с позывным \"{callsign}\" не найден.")
            return
        
        await self.db.update_ship_status(target_ship.id, status)
        await ctx.send(f"✅ Статус корабля \"{callsign}\" изменен на: {status.value}")

async def setup(bot):
    await bot.add_cog(FleetManager(bot))
