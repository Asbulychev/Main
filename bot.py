import numpy as np
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Установите здесь токен, полученный от BotFather
API_TOKEN = '8492631157:AAHoIbYZ7_v-uaGGjQiaua31mbLBiL2EVoQ' 

# Константы и функции кинематики из вашего скрипта
# (СКОПИРУЙТЕ СЮДА ФУНКЦИИ calculate_bc_from_ijk_zxz И calculate_ijk_from_bc_zxz)
B_MIN = -20.0
B_MAX = 120.0
# ... (весь код calculate_bc_from_ijk_zxz)
# ... (весь код calculate_ijk_from_bc_zxz)
# (Для краткости примера я их опускаю, но они должны быть здесь)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- ОБРАБОТЧИКИ КОМАНД И СООБЩЕНИЙ ---

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Отправляет приветственное сообщение и инструкции."""
    await message.reply(
        "👋 Привет! Я бот-калькулятор углов станка.\n\n"
        "**Доступные режимы:**\n"
        "1. **IJK -> BC:** Введите 'BC I J K' (например: `BC -60 90 -90`)\n"
        "2. **BC -> IJK:** Введите 'IJK B C' (например: `IJK -45 90`)\n\n"
        "Используется конвенция ZXZ и кинематика Стол-Стол (B вокруг Y).\n"
        f"Ограничения по B: [{B_MIN}° до {B_MAX}°]."
    )

@dp.message_handler()
async def handle_calculations(message: types.Message):
    """Обрабатывает введенные пользователем команды расчета."""
    
    parts = message.text.upper().split()
    
    if not parts:
        return

    mode = parts[0]
    
    try:
        if mode == 'BC' and len(parts) == 4:
            # Режим: IJK -> BC (Обратная кинематика)
            I, J, K = map(float, parts[1:])
            result = calculate_bc_from_ijk_zxz(I, J, K)
            
            if result:
                B, C = result
                response = (f"**Результат IJK ({I}, {J}, {K}) -> BC:**\n"
                            f"B: `{B:.3f}°`\n"
                            f"C: `{C:.3f}°`")
            else:
                response = f"⚠️ **Ошибка:** Решение не найдено в пределах ограничений оси B: [{B_MIN}° до {B_MAX}°]."

        elif mode == 'IJK' and len(parts) == 3:
            # Режим: BC -> IJK (Прямая кинематика)
            B, C = map(float, parts[1:])
            I, J, K = calculate_ijk_from_bc_zxz(B, C)
            
            response = (f"**Результат BC ({B}, {C}) -> IJK (ZXZ):**\n"
                        f"I: `{I:.3f}°`\n"
                        f"J: `{J:.3f}°`\n"
                        f"K: `{K:.3f}°` (По умолчанию K=0)")
        
        else:
            response = "Неверный формат. Пожалуйста, используйте:\n" \
                       "1. `BC I J K` (например: `BC -60 90 -90`)\n" \
                       "2. `IJK B C` (например: `IJK -45 90`)"

    except ValueError:
        response = "⚠️ Ошибка: Все углы должны быть числами."
    except Exception as e:
        # Для отладки
        logging.error(f"Произошла ошибка: {e}") 
        response = "⚠️ Произошла внутренняя ошибка расчета."

    await message.reply(response, parse_mode=types.ParseMode.MARKDOWN)

# --- ЗАПУСК БОТА ---
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

# ИЗ ПРЕДЫДУЩЕГО ОТВЕТА, ВМЕСТО КОММЕНТАРИЕВ
