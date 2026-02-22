import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Конфигурация бота"""
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "elaim.db")
    ADMIN_ROLE: str = os.getenv("ADMIN_ROLE", "Администратор")
    
    # Игровые константы
    STARTING_GOLD: int = 10000
    SALARY_PER_CREW: int = 2  # ЗР за ход
    RATION_PER_CREW: int = 1  # Пайки за ход
    
    # Потребление метана (тонн на 100 км)
    METHANE_CORVETTE: int = 20
    METHANE_FRIGATE: int = 50
    METHANE_CRUISER: int = 200

    def validate(self) -> None:
        if not self.DISCORD_TOKEN:
            raise ValueError(
                "DISCORD_TOKEN не установлен! \n\n"
                "Если вы деплоите на Railway: \n"
                "1. Зайдите во вкладку 'Variables' вашего сервиса.\n"
                "2. Добавьте переменную DISCORD_TOKEN с вашим токеном от Discord Developer Portal."
            )
