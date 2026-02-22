import discord
from discord.ext import commands
import os
import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv
# Загрузка .env из текущей (корневой) директории
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from config import Config
from models.database import Database
from utils.game_mechanics import seed_modules

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('elaim_bot')

class ElaimBot(commands.Bot):
    def __init__(self):
        self.config = Config()
        self.config.validate()
        self.db = Database(self.config.DATABASE_PATH)
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=self.config.COMMAND_PREFIX,
            intents=intents,
            help_command=None,
            description='Элаим - бот для игры Highfleet'
        )
    
    async def setup_hook(self):
        """Инициализация при старте"""
        logger.info("Инициализация базы данных...")
        
        # Убедимся, что директория для БД существует (важно для Docker / Railway Volumes)
        db_path = Path(self.config.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        await self.db.init_db()
        
        # Наполнение базы модулями
        await seed_modules(self.db)
        
        # Загрузка Cogs
        # cogs.market временно отключен, так как файл отсутствует в репозитории
        cogs = ['cogs.calculator', 'cogs.fleet', 'cogs.admin', 'cogs.combat', 'cogs.help']
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Загружен модуль: {cog}")
            except Exception as e:
                logger.error(f"Ошибка загрузки {cog}: {e}")
        
        # Синхронизация команд
        logger.info("Синхронизация команд...")
        await self.tree.sync()
    
    async def on_ready(self):
        """Событие готовности бота"""
        logger.info(f'Бот {self.user} запущен!')
        logger.info(f'ID: {self.user.id}')
        logger.info(f'Серверов: {len(self.guilds)}')
        
        # Установка статуса
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="Highfleet | !помощь"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """Обработка ошибок команд"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Не хватает аргументов. Использование: `{ctx.command.usage or ctx.command.name}`")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Неверный аргумент: {error}")
            return
        
        logger.error(f"Ошибка в команде {ctx.command}: {error}")
        await ctx.send("❌ Произошла ошибка при выполнении команды.")


async def main():
    bot = ElaimBot()
    
    try:
        await bot.start(bot.config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Завершение работы...")
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())
