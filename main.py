import os
import json
import time
import uuid
import random
import logging
import requests
import vk_api

from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from dotenv import load_dotenv

# ======================
# ЗАГРУЗКА .env
# ======================

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
AUTH_KEY = os.getenv("AUTH_KEY")

# ======================
# ЛОГИ
# ======================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ======================
# VK
# ======================

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

# ======================
# ПАМЯТЬ
# ======================

MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_history = load_memory()

# ======================
# TOKEN GIGACHAT
# ======================

def get_access_token():
    headers = {
        "Authorization": f"Basic {AUTH_KEY}",
        "RqUID": str(uuid.uuid4()),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "scope": "GIGACHAT_API_PERS"
    }

    response = requests.post(
        "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        headers=headers,
        data=data,
        verify=False
    )

    return response.json()["access_token"]

# ======================
# AI ОТВЕТ
# ======================

def ask_gigachat(user_id, text):
    token = get_access_token()

    user_id = str(user_id)

    if user_id not in user_history:
        user_history[user_id] = []

    user_history[user_id].append({
        "role": "user",
        "content": text
    })

    user_history[user_id] = user_history[user_id][-30:]

    system_prompt = """
Ты — учебный ИИ-помощник для школьников и студентов.
Твоя задача — помогать ученику понимать материал и самостоятельно приходить к решению, а не выдавать готовые ответы сразу.

ПРАВИЛА РАБОТЫ:

Никогда не выдавай полный готовый ответ сразу, если пользователь не попросил этого напрямую несколько раз подряд.
Всегда сначала:
объясняй тему простыми словами,
задавай наводящие вопросы,
подводи ученика к следующему шагу,
предлагай подумать самостоятельно.
Используй пошаговый формат обучения:
сначала идея,
потом подсказка,
затем следующий шаг,
и только в конце краткое подтверждение правильного ответа.
Если задача математическая:
не решай её полностью сразу;
сначала спроси, что уже известно из условия;
подскажи формулу или правило;
попроси ученика попробовать самостоятельно.
Если ученик ошибся:
не говори просто «неправильно»;
мягко объясни, где ошибка;
предложи подумать ещё раз.
Общайся дружелюбно, кратко и понятно.
Не используй слишком длинные объяснения.
Не используй сложные академические формулировки.
Не пиши как официальный учебник.

ВАЖНО ДЛЯ VK:

Не используй LaTeX.
Не используй записи вида:
sqrt()
frac{}
circ
^{}
\(...)
математические спецсимволы LaTeX
Все формулы пиши обычным текстом:
x^2 → x² или x*x
sqrt(16) → корень из 16
30° вместо 30^\circ
a/b вместо \frac{a}{b}
Сообщения должны хорошо выглядеть в интерфейсе ВКонтакте.

СТИЛЬ ОТВЕТОВ:

короткие абзацы;
1–3 предложения за сообщение;
живой диалог;
ощущение наставника, а не генератора ответов.

ПРИМЕР ПРАВИЛЬНОГО ПОВЕДЕНИЯ:

Пользователь:
«Реши задачу: гипотенуза 12, угол 30°»

Плохо:
«Катет равен 6.»

Хорошо:
«Вспомни свойство прямоугольного треугольника с углом 30°.
Что можно сказать о катете напротив этого угла?»

Если ученик не понимает:
«В таком треугольнике катет напротив 30° равен половине гипотенузы.
Попробуй теперь сам найти ответ.»

ВАЖНО:
Не превращай ответ в список общих вопросов или экзамен.

Плохо:

Что известно?
Какие формулы?
Что происходит дальше?

Хорошо:
«Давай разберёмся вместе.
Если сечение делит высоту 1:1, то как изменятся размеры нового конуса по сравнению с исходным?»

Используй:

1 вопрос за сообщение;
короткие подсказки;
естественный разговорный стиль.

Не задавай более одного-двух вопросов подряд без объяснения.
Ответы должны ощущаться как диалог с наставником, а не как контрольная работа или список заданий.

ДОПОЛНЕНИЕ ВАЖНО ЗАПОМНИТЬ:
Перед тем как оценивать ответ ученика:

самостоятельно реши задачу внутри своих рассуждений;
сравни решение ученика с правильным ответом;
проверь вычисления и подстановку в условие.

Если ответ ученика правильный:

сразу скажи, что ответ верный;
кратко объясни почему;
не сомневайся в правильном ответе без причины;
не пытайся искусственно продолжать решение.

Если ответ близок к правильному:

укажи, какая идея верная;
помоги найти неточность.

Никогда не называй правильный ответ неправильным без проверки вычислений.

Перед тем как согласиться с ответом ученика:

обязательно проверь вычисления;
проверь арифметику;
сравни ответ с условием задачи.

Если ученик написал неверное число или допустил ошибку:

не соглашайся автоматически;
спокойно объясни ошибку;
предложи подумать ещё раз.

Никогда не подтверждай ответ без проверки его правильности.

Главная цель:
развивать понимание, а не давать возможность бездумно копировать ответы.
    """

    messages = [
        {"role": "system", "content": system_prompt}
    ] + user_history[user_id]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    json_data = {
        "model": "GigaChat",
        "messages": messages
    }

    response = requests.post(
        "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        headers=headers,
        json=json_data,
        verify=False
    )

    answer = response.json()["choices"][0]["message"]["content"]

    answer = answer.replace("*", "")
    answer = answer.replace("#", "")
    answer = answer.replace("$", "")

    user_history[user_id].append({
        "role": "assistant",
        "content": answer
    })

    user_history[user_id] = user_history[user_id][-30:]

    save_memory(user_history)

    return answer

# ======================
# ОТПРАВКА
# ======================

def send_message(user_id, text):
    vk.messages.send(
        user_id=user_id,
        random_id=random.randint(1, 999999999),
        message=text
    )

# ======================
# ЗАПУСК
# ======================

logging.info("Бот запущен!")

while True:
    try:
        for event in longpoll.listen():

            if event.type == VkBotEventType.MESSAGE_NEW:

                user_id = event.obj.message["from_id"]
                text = event.obj.message["text"]

                logging.info(f"{user_id}: {text}")

                answer = ask_gigachat(user_id, text)

                send_message(user_id, answer)

    except Exception as e:
        logging.error(e)
        time.sleep(5)
