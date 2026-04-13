import os
import sys
import math

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


# --- ГЕНЕРАЦИЯ 2D-СХЕМЫ С УЧЕТОМ ДВУХ УГЛОВ ДЛЯ ВАЛЬМЫ ---
@app.route("/generate_scheme", methods=["POST"])
def generate_scheme():
    data = request.json
    roof_type = data.get("roof_type", "shed")
    w_input = float(data.get("width", 0))
    h_input = float(data.get("height", 0))
    pitch = float(data.get("pitch", 0))
    pitch_hip = float(data.get("pitch_hip", 0))
    
    if pitch_hip == 0:
        pitch_hip = pitch # Если второй угол не ввели, считаем их одинаковыми

    if w_input <= 0 or h_input <= 0:
        return jsonify({"svg": "<p style='color:red;'>Укажите размеры больше 0.</p>"})

    slope_factor = 1
    if 0 < pitch < 89:
        slope_factor = 1 / math.cos(math.radians(pitch))
    true_h = round(h_input * slope_factor, 2)

    max_dim = max(w_input, h_input)
    scale = 300 / max_dim if max_dim > 0 else 50
    w = w_input * scale
    h = h_input * scale
    pad = 80
    total_w = w + pad * 2
    total_h = h + pad * 2

    svg = f'<svg width="100%" height="{total_h}" viewBox="0 0 {total_w} {total_h}" xmlns="http://www.w3.org/2000/svg">'
    
    svg += '''
    <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#95a5a6" />
        </marker>
    </defs>
    '''
    svg += '''<style>
        .eaves {stroke: #2ecc71; stroke-width: 4;}   
        .rake {stroke: #f1c40f; stroke-width: 4;}    
        .ridge {stroke: #e74c3c; stroke-width: 4;}   
        .hip {stroke: #e74c3c; stroke-width: 3;}     
        .abutment {stroke: #3498db; stroke-width: 4;}
        .valley {stroke: #e67e22; stroke-width: 3;}  
        .water {stroke: #95a5a6; stroke-width: 2; marker-end: url(#arrow); stroke-dasharray: 4 4;}
        .text {font-family: sans-serif; font-size: 14px; font-weight: bold; fill: #2c3e50;}
    </style>'''
    
    cx, cy = pad, pad
    t_eaves = f"Карниз: {w_input} м"
    t_rake = f"Торец (скат): {true_h} м" if pitch > 0 else f"Торец: {h_input} м"

    if roof_type == 'shed':
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'      
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w}" y2="{cy}" class="abutment"/>'       
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+h}" class="rake"/>'           
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w}" y2="{cy+h}" class="rake"/>'       
        svg += f'<line x1="{cx+w/2}" y1="{cy+h*0.2}" x2="{cx+w/2}" y2="{cy+h*0.8}" class="water"/>'
        
        svg += f'<text x="{cx+w/2}" y="{cy-15}" text-anchor="middle" class="text">Примыкание: {w_input} м</text>'
        svg += f'<text x="{cx+w/2}" y="{cy+h+20}" text-anchor="middle" class="text">{t_eaves}</text>'
        svg += f'<text x="{cx-15}" y="{cy+h/2}" text-anchor="middle" transform="rotate(-90, {cx-15}, {cy+h/2})" class="text">{t_rake}</text>'
        svg += f'<text x="{cx+w+15}" y="{cy+h/2}" text-anchor="middle" transform="rotate(90, {cx+w+15}, {cy+h/2})" class="text">{t_rake}</text>'

    elif roof_type == 'gable':
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w}" y2="{cy}" class="eaves"/>'          
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'      
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+h}" class="rake"/>'           
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w}" y2="{cy+h}" class="rake"/>'       
        svg += f'<line x1="{cx}" y1="{cy+h/2}" x2="{cx+w}" y2="{cy+h/2}" class="ridge"/>'  
        
        svg += f'<line x1="{cx+w/2}" y1="{cy+h/2-10}" x2="{cx+w/2}" y2="{cy+h*0.1}" class="water"/>'
        svg += f'<line x1="{cx+w/2}" y1="{cy+h/2+10}" x2="{cx+w/2}" y2="{cy+h*0.9}" class="water"/>'
        
        svg += f'<text x="{cx+w/2}" y="{cy-15}" text-anchor="middle" class="text">{t_eaves}</text>'
        svg += f'<text x="{cx+w/2}" y="{cy+h+20}" text-anchor="middle" class="text">{t_eaves}</text>'
        svg += f'<text x="{cx-15}" y="{cy+h/2}" text-anchor="middle" transform="rotate(-90, {cx-15}, {cy+h/2})" class="text">{t_rake}</text>'
        svg += f'<text x="{cx+w+15}" y="{cy+h/2}" text-anchor="middle" transform="rotate(90, {cx+w+15}, {cy+h/2})" class="text">{t_rake}</text>'

    elif roof_type == 'hip':
        # Для вальмы: w - это всегда Трапеция (длина дома), h - Треугольник (ширина)
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w}" y2="{cy}" class="eaves"/>'          
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'      
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+h}" class="eaves"/>'           
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'       
        
        # Умный расчет длины конька на основе двух разных углов
        indent = h / 2
        if pitch > 0 and pitch_hip > 0 and pitch != pitch_hip:
            p1 = math.radians(pitch)
            p2 = math.radians(pitch_hip)
            height_of_roof = (h / 2) * math.tan(p1)
            indent = height_of_roof / math.tan(p2)
            if indent > w / 2: # Защита от перехлеста (шатра)
                indent = w / 2
                
        svg += f'<line x1="{cx+indent}" y1="{cy+h/2}" x2="{cx+w-indent}" y2="{cy+h/2}" class="ridge"/>'
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+indent}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+indent}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w-indent}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx+w}" y1="{cy+h}" x2="{cx+w-indent}" y2="{cy+h/2}" class="hip"/>'
            
        t_hip_side = f"Карниз вальмы: {h_input} м"
        t_trap_side = f"Карниз трап.: {w_input} м"
        svg += f'<text x="{cx+w/2}" y="{cy-15}" text-anchor="middle" class="text">{t_trap_side}</text>'
        svg += f'<text x="{cx+w/2}" y="{cy+h+20}" text-anchor="middle" class="text">{t_trap_side}</text>'
        svg += f'<text x="{cx-15}" y="{cy+h/2}" text-anchor="middle" transform="rotate(-90, {cx-15}, {cy+h/2})" class="text">{t_hip_side}</text>'
        svg += f'<text x="{cx+w+15}" y="{cy+h/2}" text-anchor="middle" transform="rotate(90, {cx+w+15}, {cy+h/2})" class="text">{t_hip_side}</text>'

    svg += '</svg>'
    
    legend = '''
    <div style="margin-top: 10px; display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; font-size: 14px; font-weight: bold; background: #fdfefe; padding: 10px; border-radius: 5px; border: 1px solid #eee;">
       <div><span style="color: #2ecc71; font-size: 18px;">■</span> Карниз</div>
       <div><span style="color: #f1c40f; font-size: 18px;">■</span> Торец</div>
       <div><span style="color: #e74c3c; font-size: 18px;">■</span> Конек/Хребет</div>
       <div><span style="color: #e67e22; font-size: 18px;">■</span> Ендова</div>
       <div><span style="color: #3498db; font-size: 18px;">■</span> Примыкание</div>
    </div>
    '''
    
    return jsonify({"svg": svg + legend})

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message")
    chat_history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Пустое сообщение"})

    formatted_contents = []
    for msg in chat_history:
        formatted_contents.append({"role": msg["role"], "parts": [{"text": msg["text"]}]})

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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)