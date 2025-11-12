
import numpy as np
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# =========================================================================
# 1. НАСТРОЙКИ И КОНСТАНТЫ
# =========================================================================

# !!! ВСТАВЬТЕ СЮДА ВАШ ТОКЕН !!!
API_TOKEN = os.getenv('BOT_TOKEN')

# Лимиты для осей (в градусах)
A_MIN, A_MAX = -120.0, 120.0
B_MIN, B_MAX = -120.0, 120.0

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# =========================================================================
# 2. КИНЕМАТИКА "BC" (B - поворот вокруг Y)
# Модель: M = R_Z(C) * R_Y(B)
# =========================================================================

def calculate_ijk_from_bc_zxz(B, C):
    """
    ПРЯМАЯ КИНЕМАТИКА (BC -> IJK, ZXZ)
    Модель: M = R_Z(C) * R_Y(B)
    """
    B_rad = np.radians(B)
    C_rad = np.radians(C)
    
    # Элементы матрицы станка M = R_Z(C) * R_Y(B)
    m13 = np.cos(C_rad) * np.sin(B_rad)
    m23 = np.sin(C_rad) * np.sin(B_rad)
    m31 = -np.sin(B_rad)
    m32 = 0.0
    m33 = np.cos(B_rad)
    
    # Угол J (из m33)
    J_rad = np.arccos(m33)
    J = np.degrees(J_rad)
    
    # Проверка на Gimbal Lock (J=0 или 180)
    if np.isclose(np.sin(J_rad), 0.0):
        I = np.degrees(np.arctan2(np.sin(C_rad), np.cos(C_rad))) # I = C
        K = 0.0
    else:
        # Угол I (из m13, m23)
        sin_I = m13 / np.sin(J_rad)
        cos_I = -m23 / np.sin(J_rad)
        I = np.degrees(np.arctan2(sin_I, cos_I))
        
        # Угол K (из m31, m32)
        sin_K = m31 / np.sin(J_rad)
        cos_K = m32 / np.sin(J_rad)
        K = np.degrees(np.arctan2(sin_K, cos_K))
        
    return I, J, K

def calculate_bc_from_ijk_zxz(I, J, K):
    """
    ОБРАТНАЯ КИНЕМАТИКА (IJK -> BC, ZXZ)
    Возвращает ДВА решения.
    """
    # Проверка на главный костыль ZXZ для этой кинематики:
    # m32 = sin(J)*cos(K) должен быть 0.
    # Это значит, K должен быть 90 или -90 (если J не 0).
    
    # Решение 1 (Предполагает K = -90)
    # B = J
    # C = I - 90
    B1 = J
    C1 = (I - 90.0 + 180) % 360 - 180 # Нормализация C в [-180, 180]

    # Решение 2 (Предполага L K = +90)
    # B = -J
    # C = I + 90
    B2 = -J
    C2 = (I + 90.0 + 180) % 360 - 180 # Нормализация C
    
    return (B1, C1), (B2, C2)

# =========================================================================
# 3. КИНЕМАТИКА "AC" (A - поворот вокруг X)
# Модель: M = R_Z(C) * R_X(A)
# =========================================================================

def calculate_ijk_from_ac_zxz(A, C):
    """
    ПРЯМАЯ КИНЕМАТИКА (AC -> IJK, ZXZ)
    Модель: M = R_Z(C) * R_X(A)
    """
    # Для этой модели M_ZXZ(I,J,K) = R_Z(I) * R_X(J) * R_Z(K)
    # M_AC = R_Z(C) * R_X(A)
    # Мы ищем I, J, K такие, что:
    # R_Z(I) * R_X(J) * R_Z(K) = R_Z(C) * R_X(A)
    # Это возможно, если I=C, J=A, K=0.
    I = C
    J = A
    K = 0.0
    return I, J, K

def calculate_ac_from_ijk_zxz(I, J, K):
    """
    ОБРАТНАЯ КИНЕМАТИКА (IJK -> AC, ZXZ)
    Возвращает ДВА решения.
    """
    # Проверка на костыль ZXZ для этой кинематики:
    # m31 = sin(J)*sin(K) должен быть 0.
    # Это значит, K должен быть 0 или 180 (если J не 0).

    # Решение 1 (Предполагает K = 0)
    # A = J
    # C = I
    A1 = J
    C1 = (I + 180) % 360 - 180 # Нормализация

    # Решение 2 (Предполагает K = 180)
    # A = -J
    # C = I + 180
    A2 = -J
    C2 = (I + 180.0 + 180) % 360 - 180 # Нормализация
    
    return (A1, C1), (A2, C2)

# =========================================================================
# 4. ОБРАБОТЧИКИ БОТА
# =========================================================================

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Отправляет приветственное сообщение и инструкции."""
    await message.reply(
        "Бот-калькулятор углов углов Эйлера для команды G68.2 (ZXZ).\n\n"
        f"**Лимиты:**\n"
        f"Ось A (вокруг X): [{A_MIN}°, {A_MAX}°]\n"
        f"Ось B (вокруг Y): [{B_MIN}°, {B_MAX}°]\n\n"
        "**Форматы команд (ZXZ):**\n\n"
        "**1. Прямая (Оси -> IJK):**\n"
        "  `AC <A> <C>` (напр. `AC 90 180`)\n"
        "  `BC <B> <C>` (напр. `BC 90 180`)\n\n"
        "**2. Обратная (IJK -> Оси):**\n"
        "  `AC <I> <J> <K>` (напр. `AC 45 30 0`)\n"
        "  `BC <I> <J> <K>` (напр. `BC 178 36 -90`)\n\n"
        "Бот всегда покажет два математических решения для обратной кинематики.",
        parse_mode=types.ParseMode.MARKDOWN
    )

def check_limit(value, min_val, max_val):
    """Проверяет, в лимите ли значение, и возвращает Emoji."""
    if min_val <= value <= max_val:
        return "✅ (В лимите)"
    return "❌ (ВНЕ лимита)"

async def format_inverse_response(solutions, axis_names, limits):
    """Форматирует ответ для двух решений."""
    name_A, name_C = axis_names
    min_val, max_val = limits
    
    (A1, C1), (A2, C2) = solutions
    
    # Проверка лимитов
    limit_check1 = check_limit(A1, min_val, max_val)
    limit_check2 = check_limit(A2, min_val, max_val)
    
    response = (
        f"**Рассчитано 2 математических решения:**\n\n"
        f"**Решение 1 (Обычно для K=0 или K=-90):**\n"
        f"  {name_A}: `{A1:.3f}°` {limit_check1}\n"
        f"  {name_C}: `{C1:.3f}°`\n\n"
        f"**Решение 2 (Обычно для K=180 или K=90):**\n"
        f"  {name_A}: `{A2:.3f}°` {limit_check2}\n"
        f"  {name_C}: `{C2:.3f}°`"
    )
    return response

@dp.message_handler()
async def handle_calculations(message: types.Message):
    """Обрабатывает введенные пользователем команды расчета."""
    
    parts = message.text.upper().split()
    response = "⚠️ Неверный формат. Используйте /help для инструкций."
    
    if len(parts) < 3:
        await message.reply(response)
        return

    mode = parts[0]
    
    try:
        # ---------------------------------------------------
        # ПРЯМАЯ КИНЕМАТИКА (Оси -> IJK), 3 аргумента
        # ---------------------------------------------------
        if len(parts) == 3:
            val1, val2 = map(float, parts[1:])
            
            if mode == 'AC':
                if not (A_MIN <= val1 <= A_MAX):
                    response = f"⚠️ Ошибка: Угол A={val1} вне лимитов [{A_MIN}, {A_MAX}]."
                else:
                    I, J, K = calculate_ijk_from_ac_zxz(val1, val2)
                    response = (f"**Результат AC ({val1}°, {val2}°) -> IJK (ZXZ):**\n"
                                f"  I: `{I:.3f}°`\n"
                                f"  J: `{J:.3f}°`\n"
                                f"  K: `{K:.3f}°`")
            
            elif mode == 'BC':
                if not (B_MIN <= val1 <= B_MAX):
                    response = f"⚠️ Ошибка: Угол B={val1} вне лимитов [{B_MIN}, {B_MAX}]."
                else:
                    I, J, K = calculate_ijk_from_bc_zxz(val1, val2)
                    response = (f"**Результат BC ({val1}°, {val2}°) -> IJK (ZXZ):**\n"
                                f"  I: `{I:.3f}°`\n"
                                f"  J: `{J:.3f}°`\n"
                                f"  K: `{K:.3f}°`")
            else:
                response = "Неизвестный режим. Используйте 'AC' или 'BC'."
        
        # ---------------------------------------------------
        # ОБРАТНАЯ КИНЕМАТИКА (IJK -> Оси), 4 аргумента
        # ---------------------------------------------------
        elif len(parts) == 4:
            I, J, K = map(float, parts[1:])
            
            if mode == 'AC':
                solutions = calculate_ac_from_ijk_zxz(I, J, K)
                response = await format_inverse_response(solutions, ("A", "C"), (A_MIN, A_MAX))
            
            elif mode == 'BC':
                solutions = calculate_bc_from_ijk_zxz(I, J, K)
                response = await format_inverse_response(solutions, ("B", "C"), (B_MIN, B_MAX))
            
            else:
                response = "Неизвестный режим. Используйте 'AC' или 'BC'."

    except ValueError:
        response = "⚠️ Ошибка: Все углы должны быть числами."
    except Exception as e:
        logging.error(f"Произошла внутренняя ошибка: {e}") 
        response = f"⚠️ Произошла внутренняя ошибка расчета: {e}"

    await message.reply(response, parse_mode=types.ParseMode.MARKDOWN)

# =========================================================================
# 5. ЗАПУСК БОТА
# =========================================================================

if __name__ == '__main__':
    logging.info("Starting bot...")
    executor.start_polling(dp, skip_updates=True)




