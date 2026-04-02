import os
import sys

# --- БРОНЯ ОТ ОШИБОК КОДИРОВКИ WINDOWS ---
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from flask import Flask, render_template, request, jsonify
from google import genai
import PIL.Image
import io

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

# --- ВСТАВЬ СВОЙ НОВЫЙ КЛЮЧ МЕЖДУ КАВЫЧКАМИ ---
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
# ---------------------------------------


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze_image():
    if "file" not in request.files:
        return jsonify({"error": "Файл не найден"})

    file = request.files["file"]
    img = PIL.Image.open(io.BytesIO(file.read()))

    prompt = """
    Ты профессиональный расчетчик кровельных материалов. Твоя задача — внимательно проанализировать чертеж или схему кровли.
    
    Шаг 1: Найди УГОЛ НАКЛОНА кровли (в градусах). Если его нет, пиши 0.
    Шаг 2: Найди все указанные размеры и классифицируй их по типам элементов. Если какого-то элемента нет, считай его равным 0. Сложи все длины для каждого типа элементов.
    Шаг 3: ВАЖНО: Выдавай площадь и размеры "В ПЛАНЕ" (как вид сверху, без учета наклона). Если ты видишь, что размеры на чертеже УЖЕ даны в скате (с учетом наклона), то выдай их, но напиши "Угол наклона: 0", чтобы калькулятор не умножил их второй раз.
    Шаг 4: Найди общую площадь кровли (часто обозначается буквой S). ЕСЛИ площадь на чертеже НЕ указана, ты должен рассчитать её самостоятельно на основе найденных размеров в плане. Пойми логику чертежа и примени геометрические формулы для площади.
    Шаг 5: Проанализируй геометрию скатов и определи тип кровли.

    Выведи ответ СТРОГО в следующем формате:
    
    Привет! Вот что мне удалось найти и рассчитать по этому чертежу:
    - Угол наклона: [цифра]
    - Общая площадь кровли: [цифра] м² (укажи: взято с чертежа ИЛИ рассчитано мной)
    - Длина карнизов: [цифра] м
    - Длина торцов (фронтонов): [цифра] м
    - Длина коньков: [цифра] м
    - Длина хребтов (вальм): [цифра] м
    - Длина ендов: [цифра] м
    - Длина примыканий: [цифра] м
    
    Верно ли я понял, что это: [выбери 1 вариант: 1) Односкатная, 2) Двухскатная, 3) Вальмовая, 4) Шатровая, 5) Многощипцовая, 6) Другая сложная кровля]?
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=[prompt, img]
        )
        return jsonify({"result": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message")
    chat_history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Пустое сообщение"})

    formatted_contents = []
    for msg in chat_history:
        formatted_contents.append(
            {"role": msg["role"], "parts": [{"text": msg["text"]}]}
        )

    formatted_contents.append({"role": "user", "parts": [{"text": user_message}]})

    sys_instruct = "Ты профи-помощник по кровле. Помогай клиенту с расчетами, терминами и отвечай на вопросы по тем данным, которые сохранены в памяти чата."

    try:
        from google.genai import types

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=formatted_contents,
            config=types.GenerateContentConfig(system_instruction=sys_instruct),
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    # Для сервера в интернете используем такие настройки:
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
