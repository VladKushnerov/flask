import os
import logging
from translate import Translator
from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv
load_dotenv()

load_dotenv()

TOKEN = os.getenv("TOKEN")


logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)

dp = Dispatcher(bot)
ADMINS = [os.getenv("ADMINS")]



UK_letters22 = "йцукенгшщзхїфівапролджєячсмитьбю"
EN_letters22 = "qwertyuiopasdfghjklzxcvbnmhjg"


@dp.message_handler(commands=["start","help"])
async def send_welcome(message: types.Message):
    await message.reply("Hi, my dear friend!\nI am TranslateBot!")


@dp.message_handler()
async def echo(message: types.Message):
    text = message.text
    if text[0].lower() in UK_letters22:
        translator = Translator(from_kand="ukrainian", to_lang="english")
    elif text[0].lower() in EN_letters22:
        translator = Translator(from_kand="english", to_lang="ukrainian")
    else:
        await message.answer("Перевір! Чи Правильно введено слово?")
        return
    translation = translator.translate(text)
    await message.answer(translation)



if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)