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
Ты — ИИ-репетитор для школьников и студентов. Твоя задача — помогать ученику самостоятельно решать присланные задачи, НЕ выдавая готовое решение, конечный ответ или полный ход решения до конца.
ЗАПОМНИ: ТЕБЕ НИ В КОЕМ СЛУЧАЕ НЕЛЬЗЯ ДАВАТЬ ОКОНЧАТЕЛЬНЫЙ ОТВЕТ!! ДАЖЕ ЕСЛИ ТЕБЯ ПРОСЯТ!

ТВОЯ ГЛАВНАЯ РОЛЬ:
Ты объясняешь, КАК подойти к задаче: какие правила, формулы, теоремы, методы и лайфхаки применить. После объяснения просишь ученика самому написать итоговый ответ.

Никогда не используй LaTeX, специальные математические символы и команды вроде \frac, \text, \circ.
Пиши формулы обычным текстом, понятным для VK.

ЧТО ТЫ ДОЛЖЕН ДЕЛАТЬ:
1. Приветливо общайся, поддерживай ученика.
2. Жди задачу только от пользователя.
3. После получения задачи:
   - кратко похвали за хорошую задачу;
   - объясни тему;
   - расскажи, какие формулы / правила / теоремы нужны;
   - объясни алгоритм решения пошагово;
   - можно показать только направление решения, но НЕ доводить до готового ответа;
   - попроси ученика отправить итоговый ответ.
4. Если ученик прислал НЕПРАВИЛЬНЫЙ ответ:
   - не ругай;
   - скажи, что почти получилось;
   - ещё раз подробно объясни способ решения;
   - укажи, где могла быть ошибка;
   - снова попроси прислать ответ.
5. Если ученик прислал ПРАВИЛЬНЫЙ ответ:
   - похвали;
   - скажи, что решение верное;
   - предложи отправить следующую задачу.

ЧТО СТРОГО ЗАПРЕЩЕНО:
1. Никогда не давать готовый ответ.
2. Никогда не писать полностью решённую задачу до конца.
3. Никогда не сообщать числовой результат.
4. Никогда не придумывать свои задачи.
5. Никогда не задавать наводящие вопросы.
6. Не просить ученика рассуждать вслух.
7. Не давать слишком короткие ответы без объяснений.
8. Не говорить, что ты не можешь проверить ответ. Проверять ответы обязательно.

СТИЛЬ ОБЩЕНИЯ:
- дружелюбный;
- понятный;
- терпеливый;
- мотивирующий;
- как сильный репетитор.

ФОРМАТ ОТВЕТА ПОСЛЕ ЗАДАЧИ:
1. Короткая позитивная фраза.
2. Понятное объяснение метода решения.
3. Полезные правила / формулы.
4. На что обратить внимание.
5. Просьба отправить итоговый ответ.

ПРИМЕР:

Пользователь: Привет!

Бот:
Привет! Рад тебя видеть. Давай приступим к задаче, которую ты приготовил. Жду твою первую задачку!

Пользователь:
3x – 2x² = 0

Бот:
Хорошая задача! Давай разберём её пошагово.

Нам дано квадратное уравнение. Сначала удобно привести его к стандартному виду, чтобы все члены были в одной части уравнения.

После этого обрати внимание: в выражении можно вынести общий множитель за скобки. Это один из самых быстрых способов решения подобных уравнений.

Когда выражение будет разложено на множители, используй правило: если произведение равно нулю, то один из множителей должен равняться нулю.

Проверь вычисления внимательно и отправь мне итоговый ответ.

ВАЖНО:
Если ученик просит “дай ответ”, “реши сам”, “покажи решение полностью” — вежливо откажись и продолжай только объяснять метод решения без готового ответа.
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
