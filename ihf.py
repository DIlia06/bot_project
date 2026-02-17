import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8337047101:AAEMepjuRafztG8HOhDPFlH6EJL14wY-"
BASE_API_URL = "http://127.0.0.1:8000/api"

ABOUT_US_URL = f"{BASE_API_URL}/core/about_us"
CREATE_APPEAL_URL = f"{BASE_API_URL}/appeals/create_appeal"
LIST_APPEALS_URL = f"{BASE_API_URL}/appeals/list"
GET_OR_CREATE_USER_URL = f"{BASE_API_URL}/users/get_or_create"

# URL для разделов каталога
CATALOG_PRINTERS_URL = f"{BASE_API_URL}/catalog/printers"
CATALOG_MFU_URL = f"{BASE_API_URL}/catalog/mfu"
CATALOG_OPTIONAL_URL = f"{BASE_API_URL}/catalog/optional"
CATALOG_CONSUMABLES_URL = f"{BASE_API_URL}/catalog/consumables"
CATALOG_SPARES_URL = f"{BASE_API_URL}/catalog/spares"
CATALOG_RELATED_URL = f"{BASE_API_URL}/catalog/related"

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

class AppealForm(StatesGroup):
    waiting_for_theme = State()
    waiting_for_message = State()

# ---------- Вспомогательные функции ----------
def get_or_create_user(telegram_id: int) -> int:
    try:
        response = requests.post(GET_OR_CREATE_USER_URL, json={"telegram_id": telegram_id}, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data["id"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при получении/создании пользователя: {e}")
        raise Exception("Не удалось идентифицировать пользователя. Попробуйте позже.")

def get_about_us() -> str:
    try:
        response = requests.get(ABOUT_US_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("text", "Информация не найдена")
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе about_us: {e}")
        return "Не удалось получить информацию. Попробуйте позже."

def create_appeal(user_id: int, theme: str, message: str) -> str:
    try:
        payload = {"user": user_id, "theme": theme, "message": message, "status": 1}
        response = requests.post(CREATE_APPEAL_URL, json=payload, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("message", "Обращение успешно создано!")
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при создании обращения: {e}")
        return "Не удалось создать обращение. Попробуйте позже."

def list_appeals(telegram_id: int) -> str:
    try:
        response = requests.get(LIST_APPEALS_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            return "Неверный формат ответа от сервера."
        user_appeals = [item for item in data if str(item.get("user")) == str(telegram_id)]
        if not user_appeals:
            return "У вас пока нет обращений."
        lines = [f"{i+1}. {appeal['message']}" for i, appeal in enumerate(user_appeals)]
        return "Ваши обращения:\n" + "\n".join(lines)
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при получении списка обращений: {e}")
        return "Не удалось загрузить список обращений. Попробуйте позже."

def get_category_items(url: str, category_name: str) -> str:
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            return f"Ошибка: неверный формат данных для раздела {category_name}."
        if not data:
            return f"В разделе «{category_name}» пока нет товаров."
        lines = [f"🔹 {item['name']}: {item['link']}" for item in data]
        return f"📌 {category_name}:\n" + "\n".join(lines)
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при получении {category_name}: {e}")
        return f"Не удалось загрузить раздел «{category_name}». Попробуйте позже."

# ---------- Клавиатуры ----------
def get_main_keyboard():
    buttons = [
        [KeyboardButton(text="📖 О нас")],
        [KeyboardButton(text="✉️ Обращения")],
        [KeyboardButton(text="🛍 Каталог")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_appeals_submenu_keyboard():
    buttons = [
        [KeyboardButton(text="📝 Создать обращение")],
        [KeyboardButton(text="📋 Просмотреть обращения")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_catalog_categories_keyboard():
    buttons = [
        [KeyboardButton(text="🖨 Принтеры")],
        [KeyboardButton(text="📠 Копиры и МФУ")],
        [KeyboardButton(text="⚙️ Опциональное оснащение")],
        [KeyboardButton(text="🖨 Расходные материалы")],
        [KeyboardButton(text="🔧 Запчасти")],
        [KeyboardButton(text="📦 Сопутствующие товары")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ---------- Обработчики главного меню ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать! Выберите раздел:", reply_markup=get_main_keyboard())

@dp.message(F.text.in_(["📖 О нас", "О нас"]))
async def about_us_handler(message: types.Message):
    await message.answer("⏳ Запрашиваю информацию...")
    await message.answer(get_about_us())

@dp.message(F.text.in_(["✉️ Обращения", "Обращения"]))
async def appeals_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите действие:", reply_markup=get_appeals_submenu_keyboard())

@dp.message(F.text.in_(["🛍 Каталог", "Каталог"]))
async def catalog_categories_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите категорию товаров:", reply_markup=get_catalog_categories_keyboard())

# ---------- Обработчики подменю обращений ----------
@dp.message(F.text.in_(["📝 Создать обращение", "Создать обращение"]))
async def create_appeal_start(message: types.Message, state: FSMContext):
    try:
        user_id = get_or_create_user(message.from_user.id)
        await state.update_data(user_id=user_id)
    except Exception as e:
        await message.answer(str(e))
        return
    await message.answer("✍️ Введите тему обращения:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AppealForm.waiting_for_theme)

@dp.message(AppealForm.waiting_for_theme)
async def process_appeal_theme(message: types.Message, state: FSMContext):
    theme = message.text.strip()
    if not theme:
        await message.answer("Тема не может быть пустой. Попробуйте снова.")
        return
    await state.update_data(theme=theme)
    await message.answer("📝 Теперь введите текст обращения:")
    await state.set_state(AppealForm.waiting_for_message)

@dp.message(AppealForm.waiting_for_message)
async def process_appeal_message(message: types.Message, state: FSMContext):
    appeal_text = message.text.strip()
    if not appeal_text:
        await message.answer("Текст не может быть пустым. Попробуйте снова.")
        return
    data = await state.get_data()
    result = create_appeal(data["user_id"], data["theme"], appeal_text)
    await message.answer(result)
    await message.answer("Что хотите сделать дальше?", reply_markup=get_appeals_submenu_keyboard())
    await state.clear()

@dp.message(F.text.in_(["📋 Просмотреть обращения", "Просмотреть обращения"]))
async def list_appeals_handler(message: types.Message):
    await message.answer("⏳ Загружаю список обращений...")
    result = list_appeals(message.from_user.id)
    await message.answer(result, reply_markup=get_appeals_submenu_keyboard())

# ---------- Обработчики разделов каталога ----------
@dp.message(F.text.in_(["🖨 Принтеры", "Принтеры"]))
async def printers_handler(message: types.Message):
    await message.answer("⏳ Загружаю принтеры...")
    result = get_category_items(CATALOG_PRINTERS_URL, "Принтеры")
    await message.answer(result, reply_markup=get_catalog_categories_keyboard())

@dp.message(F.text.in_(["📠 Копиры и МФУ", "Копиры и МФУ"]))
async def mfu_handler(message: types.Message):
    await message.answer("⏳ Загружаю копиры и МФУ...")
    result = get_category_items(CATALOG_MFU_URL, "Копиры и МФУ")
    await message.answer(result, reply_markup=get_catalog_categories_keyboard())

@dp.message(F.text.in_(["⚙️ Опциональное оснащение", "Опциональное оснащение"]))
async def optional_handler(message: types.Message):
    await message.answer("⏳ Загружаю опциональное оснащение...")
    result = get_category_items(CATALOG_OPTIONAL_URL, "Опциональное оснащение")
    await message.answer(result, reply_markup=get_catalog_categories_keyboard())

@dp.message(F.text.in_(["🖨 Расходные материалы", "Расходные материалы"]))
async def consumables_handler(message: types.Message):
    await message.answer("⏳ Загружаю расходные материалы...")
    result = get_category_items(CATALOG_CONSUMABLES_URL, "Расходные материалы")
    await message.answer(result, reply_markup=get_catalog_categories_keyboard())

@dp.message(F.text.in_(["🔧 Запчасти", "Запчасти"]))
async def spares_handler(message: types.Message):
    await message.answer("⏳ Загружаю запчасти...")
    result = get_category_items(CATALOG_SPARES_URL, "Запчасти")
    await message.answer(result, reply_markup=get_catalog_categories_keyboard())

@dp.message(F.text.in_(["📦 Сопутствующие товары", "Сопутствующие товары"]))
async def related_handler(message: types.Message):
    await message.answer("⏳ Загружаю сопутствующие товары...")
    result = get_category_items(CATALOG_RELATED_URL, "Сопутствующие товары")
    await message.answer(result, reply_markup=get_catalog_categories_keyboard())

# ---------- Обработчик "Назад" (общий) ----------
@dp.message(F.text.in_(["🔙 Назад", "Назад"]))
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard())

# ---------- Запуск ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())