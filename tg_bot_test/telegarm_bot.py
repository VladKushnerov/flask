import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from films import films
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

TOKEN = os.getenv("TOKEN")


logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)

dp = Dispatcher(bot, storage=MemoryStorage())
ADMINS = [os.getenv("ADMINS")]


async def set_default_commands(dp):
    await dp.bot.set_my_commands(
        [
            types.BotCommand(
                command="start",
                description="Запустити телеграм бот"),
            types.BotCommand(
                command="add_film",
                description="Додати новий фільм"),
            types.BotCommand(
                command="delete_film",
                description="Видалити фільм зі списку"),
            types.BotCommand(
                command="edit_film",
                description="Редагувати фільм"),
        ]
    )


async def on_startup(dp):
    await set_default_commands(dp)


def is_url(txt):
    try:
        result = urlparse(txt)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def save_films_data(films_data):
    file = open('films.py', 'w', encoding='utf-8')
    file.write('films = {\n')
    for film_name, film_info in films_data.items():
        file.write(f'    \"{film_name}\": ')
        file.write("{\n")
        for key, value in film_info.items():
            file.write(f'        \"{key}\": \"{value}\",\n')
        file.write("    },\n")
    file.write('}\n')
    file.close()


@dp.message_handler(commands="start")
async def start(message: types.Message):
    film_choice = InlineKeyboardMarkup()
    for film in films.keys():
        button = InlineKeyboardButton(text=film, callback_data=film)
        film_choice.add(button)
    await message.answer(text="Привіт! Я - бот кіноафіша!", reply_markup=film_choice)


@dp.callback_query_handler()
async def get_film_info(callback_query: types.CallbackQuery):
    if callback_query.data in films.keys():
        await bot.send_photo(callback_query.message.chat.id, films[callback_query.data]["photo"])
        url = films[callback_query.data]["site_url"]
        rating = films[callback_query.data]["rating"]
        description = films[callback_query.data]["description"]
        message = f"<b>Film url:</b> {url}\n\n<b>Info:</b> {description}\n\n<b>Rating</b> {rating}"
        await bot.send_message(callback_query.message.chat.id, message, parse_mode="html")
    else:
        await bot.send_message(callback_query.message.chat.id, text="Фільм не знайдено!")


@dp.message_handler(commands="add_film")
async def add_film(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if str(user_id) in ADMINS:
        await message.answer(text="Введи назву фільму, який ти хочеш додати!")
        await state.set_state("set_film_name")
    else:
        await message.answer(text="У тебе недостатньо прав, щоб добавити фільм, тому що ти не є Адмін!")


@dp.message_handler(state="set_film_name")
async def set_film_name(message: types.Message, state: FSMContext):
    global film_name
    if len(message.text) > 64:
        await message.answer(text="На жаль, я не можу додати цей фільм, оскільки його довжина перевищує 64 символи")
    else:
        film_name = message.text
        films[film_name] = {}
        await state.set_state("set_site_url")
        await message.answer(text="Чудово! Тепер введи посилання для нашого фільму!")


@dp.message_handler(state="set_site_url")
async def set_site_url(message: types.Message, state: FSMContext):
    global film_name
    film_site_url = message.text
    if is_url(film_site_url):
        films[film_name]["site_url"] = film_site_url
        await state.set_state("set_description")
        await message.answer(text="Чудово! Тепер введи опис для фільму!")
    else:
        await message.answer(text="Ви ввели не посилання! Спробуйте ще раз!")


@dp.message_handler(state="set_description")
async def set_description(message: types.Message, state: FSMContext):
    global film_name
    description = message.text
    films[film_name]["description"] = description
    await state.set_state("set_rating")
    await message.answer(text="Чудово! Тепер додай рейтинг до фільму!")


@dp.message_handler(state="set_rating")
async def set_rating(message: types.Message, state: FSMContext):
    global film_name
    rating = message.text
    try:
        rating = float(rating)
    except ValueError:
        await message.reply(text="Потрібно вводити число!!!")
    else:
        if rating < 0.0 or rating > 10.0:
            await message.reply(text="Введи значення у межах від 0 до 10!")
        else:
            films[film_name]["rating"] = rating
            await state.set_state("set_photo")
            await message.answer(text="Чудово! Тепер додай посилання на фото!")


@dp.message_handler(state="set_photo")
async def set_photo(message: types.Message, state: FSMContext):
    global film_name
    photo = message.text
    if is_url(photo):
        films[film_name]["photo"] = photo
        save_films_data(films)
        await state.finish()
        await message.answer(text="Супер! Фільм додано!")
    else:
        await message.answer(text="Ви ввели не посилання!")


@dp.message_handler(commands="delete_film")
async def delete_film_by_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if str(user_id) in ADMINS:
        list_films = list(films.keys())
        if not list_films:
            await message.reply(text="Список фільмів порожній!")
            return
        film_choice = InlineKeyboardMarkup(row_width=1)
        for film in list_films:
            button = InlineKeyboardButton(text=film, callback_data=f"delete_{film}")
            film_choice.insert(button)
        await state.set_state("delete_film")
        await message.reply(text="Оберіть фільм, який ви хочете видалити!", reply_markup=film_choice)
    else:
        await message.reply(text="Ти не є ADMIN! Отож, ти не можеш видалити фільм!")


@dp.callback_query_handler(lambda query: query.data.startswith("delete_"), state="delete_film")
async def delete_film_on_callback(query: types.CallbackQuery, state: FSMContext):
    user_id = query.from_user.id
    if str(user_id) in ADMINS:
        film_name = query.data.split("delete_")[1]
        if film_name.title() in films:
            del films[film_name.title()]
            save_films_data(films)
            await state.finish()
            await bot.answer_callback_query(
                query.id,
                text=f"Фільм {film_name} було успішно видалено!",
                show_alert=True
            )
        if film_name in films:
            del films[film_name]
            save_films_data(films)
            await state.finish()
            await bot.answer_callback_query(
                query.id,
                text=f"Фільм {film_name} було успішно видалено!",
                show_alert=True
            )
        else:
            await state.finish()
            await bot.answer_callback_query(
                query.id,
                text=f"Фільм {film_name} не було знайдено!",
                show_alert=True
            )
    else:
        await bot.send_message(text="Ти не є адміном!")


@dp.message_handler(commands="edit_film")
async def edit_film(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if str(user_id) in ADMINS:
        film_for_editing = list(films.keys())
        if not film_for_editing:
            await message.reply(text="Список фільмів порожній. Спершу добавте фільм!")
            return
        film_choice = InlineKeyboardMarkup(row_width=1)
        for film in film_for_editing:
            button = InlineKeyboardButton(text=film, callback_data=f"{film}")
            film_choice.insert(button)
        await state.set_state("edit_film")
        await message.reply(text="Обeріть фільм для редагування", reply_markup=film_choice)
    else:
        await message.reply(text="Ти не є ADMIN! Отож, ти не можеш видалити фільм!")


@dp.callback_query_handler(state="edit_film")
async def edit_film(query: types.CallbackQuery, state: FSMContext):
    global film_name_from_button
    film_name_from_button = query.data
    if film_name_from_button in films.keys():
        film_info = InlineKeyboardMarkup()
        for info in films[film_name_from_button].keys():
            button = InlineKeyboardButton(text=info, callback_data=info)
            film_info.add(button)
        await state.set_state("choose_info_about_film")
        await bot.send_message(query.message.chat.id, text="Вибери одну із опцій!", reply_markup=film_info)
    else:
        await bot.send_message(query.message.chat.id, text="Немає фільмів!")


@dp.callback_query_handler(state="choose_info_about_film")
async def choose_info_about_film(query: types.CallbackQuery, state: FSMContext):
    name_from_button = query.data
    if name_from_button == "site_url":
        await state.set_state("site_url_edit")
        await bot.send_message(query.message.chat.id, text=f"Введи нове посилання для site_url для фільму {film_name_from_button}")
    if name_from_button == "photo":
        await state.set_state("photo_edit")
        await bot.send_message(query.message.chat.id, text=f"Введи нове посилання для photo для фільму {film_name_from_button}")
    if name_from_button == "description":
        await state.set_state("description_edit")
        await bot.send_message(query.message.chat.id, text=f"Введи новий опис для фільму {film_name_from_button}")
    if name_from_button == "rating":
        await state.set_state("rating_edit")
        await bot.send_message(query.message.chat.id, text=f"Введи новий опис для фільму {film_name_from_button}")


@dp.message_handler(state="site_url_edit")
async def site_url_edit(message: types.Message, state: FSMContext):
    site_url = message.text
    if is_url(site_url):
        films[film_name_from_button]["site_url"] = site_url
        save_films_data(films)
        await state.finish()
        await message.reply(text=f"Посилання для фільму {film_name_from_button}")
    else:
        await message.reply(text=f"Введи посилання!")


@dp.message_handler(state="photo_edit")
async def photo_edit(message: types.Message, state: FSMContext):
    photo = message.text
    if is_url(photo):
        films[film_name_from_button]["photo"] = photo
        save_films_data(films)
        await state.finish()
        await message.reply(text=f"Посилання для фото для фільму {film_name_from_button} змінено")
    else:
        await message.reply(text="Введи посилання!")


@dp.message_handler(state="description_edit")
async def description_edit(message: types.Message, state: FSMContext):
    description = message.text
    films[film_name_from_button]["description"] = description
    save_films_data(films)
    await state.finish()
    await message.reply(text=f"Опис для фільму {film_name_from_button} змінено!")


@dp.message_handler(state="rating_edit")
async def rating_edit(message:types.Message, state: FSMContext):
    try:
        rating = float(message.text)
    except ValueError:
        await message.reply(text="Потрібно вводити число!!!")
    else:
        if rating < 0.0 or rating > 10.0:
            await message.reply(text="Введи значення у межах від 0 до 10!")
        else:
            films[film_name_from_button]["rating"] = rating
            save_films_data(films)
            await state.finish()
            await message.reply(text=f"Рейтинг для фільму {film_name_from_button} змінено!")


if __name__ == "__main__":
    executor.start_polling(
        dp,
        on_startup=on_startup
    )
