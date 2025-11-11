
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
import numpy as np



# Установите здесь токен, полученный от BotFather
API_TOKEN = '8492631157:AAHoIbYZ7_v-uaGGjQiaua31mbLBiL2EVoQ' 

# Константы и функции кинематики из вашего скрипта



def calculate_ijk_from_bc_zxz(B, C):
	"""
	ПРЯМАЯ КИНЕМАТИКА (B, C -> I, J, K)
	Модель: M = R_Z(C) * R_Y(B)
	"""
	
	B_rad = np.radians(B)
	C_rad = np.radians(C)
	
	# Элементы матрицы станка M = R_Z(C) * R_Y(B)
	m11 = np.cos(C_rad) * np.cos(B_rad)
	m21 = np.sin(C_rad) * np.cos(B_rad)
	m31 = -np.sin(B_rad)
	
	m13 = np.cos(C_rad) * np.sin(B_rad)
	m23 = np.sin(C_rad) * np.sin(B_rad)
	m33 = np.cos(B_rad)
	
	# Декомпозиция ZXZ (I, J, K)
	
	# Угол J
	J_rad = np.arccos(m33)
	J = np.degrees(J_rad)
	
	# Проверка на особый случай (Gimbal Lock)
	if np.isclose(J, 0.0) or np.isclose(J, 180.0):
		# Если J=0 или 180, sin(J) = 0.
		I_rad = np.arctan2(m21, m11)
		I = np.degrees(I_rad)
		K = 0.0 # По соглашению
		
	else:
		# Стандартный расчет
		sin_J = np.sin(J_rad)
		
		# Угол I: sI*sJ = m13; -cI*sJ = m23
		sin_I = m13 / sin_J
		cos_I = -m23 / sin_J
		I_rad = np.arctan2(sin_I, cos_I)
		I = np.degrees(I_rad)
		
		# Угол K: sJ*sK = m31; sJ*cK = m32 (где m32=0)
		sin_K = m31 / sin_J
		cos_K = 0.0 # m32 = 0 в вашей кинематике (Rz*Ry)
		K_rad = np.arctan2(sin_K, cos_K)
		K = np.degrees(K_rad)
		
	return I, J, K




def calculate_bc_from_ijk_zxz(I, J, K):
	"""
	ОБРАТНАЯ КИНЕМАТИКА (I, J, K -> B, C)
	Модель: M = R_Z(C) * R_Y(B)
	Логика СЧПУ: Приоритет B=J (положительный наклон), если B в лимитах.
	"""
	
	J_rad = np.radians(J)
	K_rad = np.radians(K)
	
	# Проверка математического ограничения (m32 == 0)
	m32_euler = np.sin(J_rad) * np.cos(K_rad)
	if not np.isclose(m32_euler, 0.0, atol=1e-5):
		msg = ("Ошибка: Недопустимая комбинация IJK. Для данной кинематики "
			   "требуется, чтобы K был 90/-90 (или J 0/180).")
		return None, None, msg # Возвращаем 2 None для B, C и сообщение

	solution_found = False
	B_final = None
	C_final = None
	
	# --- Попытка 1: Решение 1 (Предпочтительное) ---
	# B = J
	# C = I - 90
	B_sol1 = J
	C_sol1 = (I - 90.0 + 180) % 360 - 180 # Нормализуем C в [-180, 180]
	
	if B_MIN <= B_sol1 <= B_MAX:
		B_final = B_sol1
		C_final = C_sol1
		solution_found = True

	# --- Попытка 2: Решение 2 (Альтернативное) ---
	# B = -J
	# C = I + 90
	if not solution_found:
		B_sol2 = -J
		C_sol2 = (I + 90.0 + 180) % 360 - 180 # Нормализуем C
		
		if B_MIN <= B_sol2 <= B_MAX:
			B_final = B_sol2
			C_final = C_sol2
			solution_found = True

	# 4. Возврат результата
	if solution_found:
		return B_final, C_final, None
	else:
		msg = f"Ошибка: Оба решения (B={J:.3f} и B={-J:.3f}) вне лимитов оси B: [{B_MIN}, {B_MAX}]."
		return None, None, msg




B_MIN = -20.0
B_MAX = 120.0
# ... (весь код calculate_bc_from_ijk_zxz)
# ... (весь код calculate_ijk_from_bc_zxz)
# (Для краткости примера я их опускаю, но они должны быть здесь)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ОБРАБОТЧИКИ КОМАНД И СООБЩЕНИЙ ---


@dp.message(Command("start"))
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

@dp.message()
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
			B_res, C_res, error_msg = calculate_bc_from_ijk_zxz(I, J, K)
			
			if B_res is not None:
				response = (f"Результат IJK ({I:.3f}, {J:.3f}, {K:.3f}) -> BC:\n"
							f"B: {B_res:.3f}°\n"
							f"C: {C_res:.3f}°")
			else:
				response = f"⚠️ Ошибка расчета: {error_msg}"

		elif mode == 'IJK' and len(parts) == 3:
			# Режим: BC -> IJK (Прямая кинематика)
			B, C = map(float, parts[1:])
			
			if not (B_MIN <= B <= B_MAX):
				 response = f"⚠️ Ошибка: Угол B={B:.3f}° находится вне лимитов станка [{B_MIN}° до {B_MAX}°]."
			else:
				I, J, K = calculate_ijk_from_bc_zxz(B, C)
			
				response = (f"Результат BC ({B:.3f}, {C:.3f}) -> IJK (ZXZ):\n"
							f"I: {I:.3f}°\n"
							f"J: {J:.3f}°\n"
							f"K: {K:.3f}°")
		
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

	await message.reply(response)

# --- ЗАПУСК БОТА ---


async def main():
	await dp.start_polling(bot)


if __name__ == '__main__':
	#executor.start_polling(dp, skip_updates=True)
	asyncio.run(main())

# СЮДА НУЖНО СКОПИРОВАТЬ ВЕСЬ КОД calculate_bc_from_ijk_zxz И calculate_ijk_from_bc_zxz
# ИЗ ПРЕДЫДУЩЕГО ОТВЕТА, ВМЕСТО КОММЕНТАРИЕВ