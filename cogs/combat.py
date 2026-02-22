import discord
from discord.ext import commands
import asyncio
import random
import time
from models.database import Database
from models.schemas import ShipModule, ShipStatus
from utils.game_mechanics import calculate_ship_combat_stats, simulate_volley, generate_debris_field

class BattleState:
    def __init__(self, attacker_fleet, defender_fleet, attacker_ships, defender_ships, distance):
        self.attacker_fleet = attacker_fleet
        self.defender_fleet = defender_fleet
        self.distance = distance
        self.turn = 1
        self.max_turns = 10
        self.logs = []
        
        # Prepare combat stats
        self.a_stats = [calculate_ship_combat_stats(s) for s in attacker_ships]
        self.d_stats = [calculate_ship_combat_stats(s) for s in defender_ships]
        
        # Store max_hp for damage percentage calculations
        for s in self.a_stats:
            s['max_hp'] = s['hp']
        for s in self.d_stats:
            s['max_hp'] = s['hp']
        
        # Map IDs to original objects for final updates
        self.a_ships_map = {s.id: s for s in attacker_ships}
        self.d_ships_map = {s.id: s for s in defender_ships}

    @property
    def is_over(self):
        a_alive = any(s['hp'] > 0 for s in self.a_stats)
        d_alive = any(s['hp'] > 0 for s in self.d_stats)
        return not a_alive or not d_alive or self.turn > self.max_turns

    def get_progress_bar(self):
        percent = (self.turn / self.max_turns)
        filled = int(percent * 10)
        bar = "█" * filled + "░" * (10 - filled)
        return f"[{bar}] {self.turn}/{self.max_turns}"

class BattleView(discord.ui.View):
    def __init__(self, cog, battle: BattleState, ctx):
        super().__init__(timeout=300)
        self.cog = cog
        self.battle = battle
        self.ctx = ctx
        self.message = None

    async def update_embed(self, finished=False, result_text=None):
        color = 0xe74c3c if not finished else 0x2ecc71
        
        desc = (
            f"**{self.battle.attacker_fleet.name}** vs **{self.battle.defender_fleet.name}**\n"
            f"Дистанция: {self.battle.distance} км\n"
            f"Ход: {self.battle.get_progress_bar()}\n\n"
        )
        
        if self.battle.logs:
            last_logs = "\n".join(self.battle.logs[-5:]) # Show last 5 entries
            desc += f"📜 **Ход боя:**\n{last_logs}\n"
            
        if result_text:
            desc += f"\n🏆 **{result_text}**"

        embed = discord.Embed(
            title="⚔️ Сражение",
            description=desc,
            color=color
        )
        
        # Status Fields
        a_status = "\n".join([f"{s['callsign']}: {int(s['hp'])} HP" for s in self.battle.a_stats])
        d_status = "\n".join([f"{s['callsign']}: {int(s['hp'])} HP" for s in self.battle.d_stats])
        
        embed.add_field(name="Атакующие", value=a_status or "Уничтожены", inline=True)
        embed.add_field(name="Защитники", value=d_status or "Уничтожены", inline=True)

        if self.message:
            await self.message.edit(embed=embed, view=self if not finished else None)

    @discord.ui.button(label="⚔️ Атака", style=discord.ButtonStyle.danger, custom_id="battle_attack")
    async def attack_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.battle.attacker_fleet.user_id and interaction.user.id != self.battle.defender_fleet.user_id:
             await interaction.response.send_message("❌ Вы не участвуете в этом бою.", ephemeral=True)
             return

        await interaction.response.defer()
        
        # Simulate Turn
        round_log = []
        
        # 1. Attacker Volley
        active_defenders = [s for s in self.battle.d_stats if s['hp'] > 0]
        if active_defenders:
            for att in [s for s in self.battle.a_stats if s['hp'] > 0]:
                target = random.choice(active_defenders)
                logs, dmg = simulate_volley(att, target)
                target['hp'] -= dmg
                round_log.extend(logs)
                if target['hp'] <= 0:
                     round_log.append(f"💀 **{target['callsign']}** уничтожен!")

        # 2. Defender Volley
        active_attackers = [s for s in self.battle.a_stats if s['hp'] > 0]
        if active_attackers:
            for deff in [s for s in self.battle.d_stats if s['hp'] > 0]:
                 target = random.choice(active_attackers)
                 logs, dmg = simulate_volley(deff, target)
                 target['hp'] -= dmg
                 round_log.extend(logs)
                 if target['hp'] <= 0:
                     round_log.append(f"💀 **{target['callsign']}** уничтожен!")
        
        self.battle.logs.extend(round_log)
        self.battle.turn += 1
        
        # Check End Condition
        if self.battle.is_over:
            await self.end_battle()
        else:
            await self.update_embed()

    @discord.ui.button(label="🏳️ Отступление", style=discord.ButtonStyle.secondary, custom_id="battle_retreat")
    async def retreat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.battle.attacker_fleet.user_id and interaction.user.id != self.battle.defender_fleet.user_id:
             await interaction.response.send_message("❌ Вы не участвуете в этом бою.", ephemeral=True)
             return
             
        # Simple retreat logic: 50% chance
        if random.random() < 0.5:
            await interaction.response.send_message("💨 **Отступление успешно!** Бой завершен.", ephemeral=False)
            await self.end_battle(reason="retreat")
        else:
            await interaction.response.send_message("❌ **Не удалось отступить!** Противник перехватил маневр.", ephemeral=True)
            self.battle.logs.append("⚠️ Попытка отступления провалилась!")
            await self.update_embed()

    @discord.ui.button(label="🛑 Отмена (Админ)", style=discord.ButtonStyle.grey, custom_id="battle_cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Admin Check
        if not interaction.user.guild_permissions.administrator:
             await interaction.response.send_message("❌ Только администратор может отменить бой.", ephemeral=True)
             return
        
        await interaction.response.send_message("🛑 **Бой остановлен администратором.**", ephemeral=False)
        self.stop()
        await self.update_embed(finished=True, result_text="Бой отменен")

    async def end_battle(self, reason="normal"):
        self.stop()
        
        # Determine Winner
        a_alive = any(s['hp'] > 0 for s in self.battle.a_stats)
        d_alive = any(s['hp'] > 0 for s in self.battle.d_stats)
        
        result_text = "Ничья"
        if reason == "retreat":
            result_text = "Бой прерван отступлением"
        elif a_alive and not d_alive:
            result_text = f"Победа {self.battle.attacker_fleet.name}!"
        elif d_alive and not a_alive:
            result_text = f"Победа {self.battle.defender_fleet.name}!"
            
        await self.update_embed(finished=True, result_text=result_text)
        
        # Apply Damage to DB
        await self.apply_damage()
        
        # Generate Debris
        if reason == "normal":
            await self.generate_loot()

    async def apply_damage(self):
        # Update ships based on final HP
        for stats in self.battle.a_stats + self.battle.d_stats:
            ship_id = stats['id']
            hp_percent = stats['hp'] / stats.get('max_hp', 100) # Assuming max_hp is roughly tracked or just check dead
            
            status = ShipStatus.OPERATIONAL
            if stats['hp'] <= 0:
                status = ShipStatus.DESTROYED
            elif hp_percent < 0.3:
                status = ShipStatus.CRITICAL_DAMAGE
            elif hp_percent < 0.6:
                status = ShipStatus.MODERATE_DAMAGE
            elif hp_percent < 0.9:
                status = ShipStatus.LIGHT_DAMAGE
            
            await self.cog.db.update_ship_status(ship_id, status)
            # If destroyed, maybe delete? For now just set status.
            
    async def generate_loot(self):
        # Collect destroyed ships
        destroyed_stats = [s for s in self.battle.a_stats + self.battle.d_stats if s['hp'] <= 0]
        
        if not destroyed_stats:
            return

        # Fetch original ships to get modules
        destroyed_ships = []
        for s in destroyed_stats:
            ship = self.battle.a_ships_map.get(s['id']) or self.battle.d_ships_map.get(s['id'])
            if ship:
                destroyed_ships.append(ship)
        
        # Generate debris
        debris = generate_debris_field(destroyed_ships, guaranteed_weapons=True)
        if debris:
            view = DebrisView(self.cog, debris, self.ctx.author)
            await self.ctx.send("🛰️ **Обнаружены обломки!**", view=view)


class Combat(commands.Cog):
    """Система боя и разрушений"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db: Database = bot.db
        self.active_battles = {}

    @commands.command(name="бой", aliases=["battle", "fight"])
    async def start_battle(self, ctx, enemy: discord.Member, distance: int = 10):
        """
        Начать бой с игроком
        !бой @враг [дистанция]
        """
        if distance > 20:
            await ctx.send("❌ Слишком большая дистанция для начала боя (макс. 20 км).")
            return
            
        attacker_fleet = await self.db.get_fleet_by_user(ctx.author.id, ctx.guild.id)
        defender_fleet = await self.db.get_fleet_by_user(enemy.id, ctx.guild.id)
        
        if not attacker_fleet or not defender_fleet:
            await ctx.send("❌ У одного из участников нет флотилии.")
            return

        # Fetch ships
        a_ships = await self.db.get_ships_by_fleet(attacker_fleet.id)
        d_ships = await self.db.get_ships_by_fleet(defender_fleet.id)
        
        # Populate modules
        for s in a_ships: 
            modules_data = await self.db.get_ship_modules(s.id)
            s.modules = [ShipModule(**m) for m in modules_data]
            
        for s in d_ships: 
            modules_data = await self.db.get_ship_modules(s.id)
            s.modules = [ShipModule(**m) for m in modules_data]
        
        # Filter operational ships
        a_combat_ships = [s for s in a_ships if s.status not in [ShipStatus.DESTROYED, ShipStatus.CRITICAL_DAMAGE]]
        d_combat_ships = [s for s in d_ships if s.status not in [ShipStatus.DESTROYED, ShipStatus.CRITICAL_DAMAGE]]

        if not a_combat_ships or not d_combat_ships:
            await ctx.send("❌ У одной из сторон нет боеспособных кораблей.")
            return

        # Initialize Battle
        battle = BattleState(attacker_fleet, defender_fleet, a_combat_ships, d_combat_ships, distance)
        view = BattleView(self, battle, ctx)
        
        # Send initial message
        embed = discord.Embed(title="⚔️ Подготовка к бою...", description="Инициализация систем...", color=0xe74c3c)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg
        await view.update_embed() # Updates the embed with correct stats


class DebrisView(discord.ui.View):
    def __init__(self, cog, debris_items, owner):
        super().__init__(timeout=60)
        self.cog = cog
        self.debris = debris_items
        self.owner = owner
        
        for i, item in enumerate(self.debris[:5]): # Max 5 buttons for now
            mod_label = "☢️" if item.get('modifier') == "radiation" else "💣" if item.get('modifier') == "explosive" else ""
            label = f"{mod_label} {item['name']} ({item.get('amount', 1)})"
            self.add_item(DebrisButton(item, label, i))

class DebrisButton(discord.ui.Button):
    def __init__(self, item, label, index):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, custom_id=f"debris_{index}")
        self.item = item
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        # Hazard Check
        if self.item.get('modifier') == "radiation":
            if random.random() < 0.7:
                await interaction.response.send_message("☢️ **АВАРИЯ!** Вы получили дозу радиации при попытке сбора. Экипаж пострадал!", ephemeral=True)
                self.disabled = True
                await interaction.message.edit(view=self.view)
                return

        if self.item.get('modifier') == "explosive":
             pass # Simplify

        # Give item
        msg = ""
        fleet = await self.view.cog.db.get_fleet_by_user(interaction.user.id, interaction.guild.id)
        
        if self.item['type'] == 'resource':
            if self.item['name'] == 'Топливо':
                await self.view.cog.db.update_fleet_resources(fleet.id, methane=fleet.methane + self.item['amount'])
                msg = f"Вы собрали {self.item['amount']} тонн топлива."
            elif self.item['name'] == 'Боеприпасы':
                 msg = f"Вы собрали боеприпасы."
                 
        elif self.item['type'] == 'module':
            await self.view.cog.db.add_module_to_inventory(fleet.id, self.item['module_id'], 1)
            msg = f"Вы подобрали модуль: {self.item['name']}"

        self.disabled = True
        self.style = discord.ButtonStyle.success
        await interaction.response.send_message(f"✅ {msg}", ephemeral=True)
        await interaction.message.edit(view=self.view)

async def setup(bot):
    await bot.add_cog(Combat(bot))
