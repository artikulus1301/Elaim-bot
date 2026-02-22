import discord
from discord.ext import commands
from models.database import Database
from utils.helpers import format_currency

def is_admin(ctx):
    """Проверка прав администратора"""
    admin_role = discord.utils.get(ctx.guild.roles, name=ctx.bot.config.ADMIN_ROLE)
    if admin_role and admin_role in ctx.author.roles:
        return True
    return ctx.author.guild_permissions.administrator

class AdminCommands(commands.Cog):
    """Административные команды для управления игрой"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db: Database = bot.db
    
    @commands.command(name="ход", aliases=["turn", "next_turn"])
    @commands.check(is_admin)
    async def process_turn(self, ctx):
        """
        [АДМИН] Обработать игровой ход для всех флотов
        Списывает зарплату и пайки, обновляет счетчик ходов
        """
        # Получаем все флоты в гильдии
        async with self.db.get_db() as db_conn:
            cursor = await db_conn.execute(
                "SELECT * FROM fleets WHERE guild_id = ?", (ctx.guild.id,)
            )
            rows = await cursor.fetchall()
            fleets = [dict(row) for row in rows]
        
        if not fleets:
            await ctx.send("❌ В этой гильдии нет зарегистрированных флотов.")
            return
        
        embed = discord.Embed(
            title=f"🎲 Игровой ход #{fleets[0]['turn_count'] + 1}",
            description="Обработка ресурсов флотов...",
            color=0xf39c12
        )
        message = await ctx.send(embed=embed)
        
        results = []
        errors = []
        
        for fleet_data in fleets:
            fleet_id = fleet_data['id']
            fleet_full = await self.db.get_fleet_with_ships(fleet_id)
            
            if not fleet_full or not fleet_full.ships:
                continue
            
            # Расчет расходов
            salary = fleet_full.salary_per_turn
            rations_needed = fleet_full.rations_per_turn
            
            # Проверка ресурсов
            if fleet_data['gold'] < salary:
                errors.append(f"⚠️ **{fleet_data['name']}**: Недостаточно золота ({fleet_data['gold']}/{salary})")
                continue
            
            if fleet_data['rations'] < rations_needed:
                errors.append(f"⚠️ **{fleet_data['name']}**: Недостаточно пайков ({fleet_data['rations']}/{rations_needed})")
                continue
            
            # Применяем ход
            try:
                await self.db.increment_turn(fleet_id, salary, rations_needed)
                new_fleet = await self.db.get_fleet(fleet_id)
                
                results.append({
                    'name': fleet_data['name'],
                    'leader': fleet_data['leader_name'],
                    'salary': salary,
                    'rations': rations_needed,
                    'gold_left': new_fleet.gold,
                    'rations_left': new_fleet.rations,
                    'turn': new_fleet.turn_count
                })
            except Exception as e:
                errors.append(f"❌ **{fleet_data['name']}**: Ошибка обработки - {str(e)}")
        
        # Формируем отчет
        if results:
            report_text = ""
            for res in results:
                report_text += (
                    f"**{res['name']}** (Тархан: {res['leader']})\n"
                    f"├ Списано: {format_currency(res['salary'])}, {res['rations']} пайков\n"
                    f"└ Остаток: {format_currency(res['gold_left'])}, {res['rations_left']} пайков\n\n"
                )
            
            embed.add_field(
                name="✅ Успешно обработано",
                value=report_text[:1024],
                inline=False
            )
        
        if errors:
            embed.add_field(
                name="⚠️ Проблемы",
                value="\n".join(errors)[:1024],
                inline=False
            )
        
        embed.color = 0x2ecc71 if not errors else 0xe67e22
        await message.edit(embed=embed)
    
    @commands.command(name="дать_ресурсы", aliases=["give_resources", "ресурсы"])
    @commands.check(is_admin)
    async def give_resources(self, ctx, member: discord.Member, resource: str, amount: int):
        """
        [АДМИН] Выдать ресурсы игроку
        Использование: !дать_ресурсы @игрок [золото/пайки/метан] [количество]
        """
        fleet = await self.db.get_fleet_by_user(member.id, ctx.guild.id)
        if not fleet:
            await ctx.send(f"❌ У {member.mention} нет флотилии.")
            return
        
        resource_map = {
            'золото': 'gold',
            'золотые': 'gold',
            'зр': 'gold',
            'gold': 'gold',
            'пайки': 'rations',
            'провиант': 'rations',
            'rations': 'rations',
            'метан': 'methane',
            'топливо': 'methane',
            'methane': 'methane',
            'fuel': 'methane'
        }
        
        res_key = resource_map.get(resource.lower())
        if not res_key:
            await ctx.send("❌ Неизвестный ресурс. Доступные: золото, пайки, метан")
            return
        
        # Обновляем ресурсы
        current = getattr(fleet, res_key)
        new_amount = current + amount
        
        await self.db.update_fleet_resources(fleet.id, **{res_key: new_amount})
        
        resource_names = {
            'gold': 'Золотые рубли',
            'rations': 'Пайки',
            'methane': 'Метан (тонны)'
        }
        
        await ctx.send(
            f"✅ {member.mention} получил **{amount:,}** {resource_names[res_key]}\n"
            f"Было: {current:,} → Стало: {new_amount:,}"
        )
    
    @commands.command(name="сбросить", aliases=["reset", "удалить_флот"])
    @commands.check(is_admin)
    async def reset_fleet(self, ctx, member: discord.Member):
        """[АДМИН] Полностью удалить флот игрока"""
        fleet = await self.db.get_fleet_by_user(member.id, ctx.guild.id)
        if not fleet:
            await ctx.send(f"❌ У {member.mention} нет флотилии.")
            return
        
        # Удаляем корабли
        ships = await self.db.get_ships_by_fleet(fleet.id)
        for ship in ships:
            await self.db.remove_ship(ship.id)
        
        # Удаляем флот
        async with self.db.get_db() as db_conn:
            await db_conn.execute("DELETE FROM fleets WHERE id = ?", (fleet.id,))
            await db_conn.commit()
        
        await ctx.send(f"✅ Флотилия игрока {member.mention} полностью удалена.")
    
    @process_turn.error
    @give_resources.error
    @reset_fleet.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ У вас нет прав администратора для этой команды.")
        else:
            raise error

    @commands.command(name="админ_инвентарь", aliases=["admin_inv_check", "aic"])
    @commands.check(is_admin)
    async def admin_inv_check(self, ctx, member: discord.Member):
        """[АДМИН] Посмотреть инвентарь игрока"""
        fleet = await self.db.get_fleet_by_user(member.id, ctx.guild.id)
        if not fleet:
            await ctx.send(f"❌ У {member.mention} нет флотилии.")
            return

        items = await self.db.get_inventory(fleet.id)
        if not items:
            await ctx.send(f"📦 Инвентарь {member.mention} пуст.")
            return

        text = ""
        for item in items:
            module = item['module']
            text += f"`ID: {module['id']}` **{module['name']}** (x{item['count']})\n"
        
        embed = discord.Embed(
            title=f"📦 Инвентарь: {fleet.name}",
            description=text,
            color=0x9b59b6
        )
        await ctx.send(embed=embed)

    @commands.command(name="админ_добавить", aliases=["admin_inv_add", "aia"])
    @commands.check(is_admin)
    async def admin_inv_add(self, ctx, member: discord.Member, item_id: int, count: int = 1):
        """[АДМИН] Добавить предмет игроку"""
        fleet = await self.db.get_fleet_by_user(member.id, ctx.guild.id)
        if not fleet:
            await ctx.send(f"❌ У {member.mention} нет флотилии.")
            return

        module = await self.db.get_module(item_id)
        if not module:
            await ctx.send(f"❌ Модуль с ID {item_id} не найден.")
            return

        await self.db.add_module_to_inventory(fleet.id, item_id, count)
        await ctx.send(f"✅ Добавлено: **{module['name']}** (x{count}) игроку {member.mention}")

    @commands.command(name="админ_удалить", aliases=["admin_inv_remove", "air"])
    @commands.check(is_admin)
    async def admin_inv_remove(self, ctx, member: discord.Member, item_id: int, count: int = 1):
        """[АДМИН] Удалить предмет у игрока"""
        fleet = await self.db.get_fleet_by_user(member.id, ctx.guild.id)
        if not fleet:
            await ctx.send(f"❌ У {member.mention} нет флотилии.")
            return

        success = await self.db.remove_module_from_inventory(fleet.id, item_id, count)
        if success:
            await ctx.send(f"✅ Предмет (ID: {item_id}) удален у {member.mention} (x{count})")
        else:
            await ctx.send(f"❌ Не удалось удалить предмет (возможно, его нет или меньше чем {count}).")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
