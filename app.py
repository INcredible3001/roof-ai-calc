import os
import sys
import math

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

# ТВОЙ КЛЮЧ
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

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
    Ты профессиональный расчетчик кровельных материалов.
    Найди УГОЛ НАКЛОНА, общую площадь и все размеры в плане.
    Выведи ответ списком и определи тип кровли (Односкатная, Двухскатная, Вальмовая, Шатровая, Многощипцовая и т.д.).
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, img])
        return jsonify({"result": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/generate_scheme", methods=["POST"])
def generate_scheme():
    data = request.json
    roof_type = data.get("roof_type", "shed")
    
    w_input = float(data.get("width", 0))   
    h_input = float(data.get("height", 0))  
    ridge_len = float(data.get("ridge", 0))

    if w_input <= 0 or h_input <= 0:
        return jsonify({"svg": "<p style='color:red;'>Укажите базовые размеры больше 0.</p>"})

    max_dim = max(w_input, h_input)
    scale = 350 / max_dim if max_dim > 0 else 50
    w = w_input * scale
    h = h_input * scale
    pad = 90
    total_w = w + pad * 2
    total_h = h + pad * 2

    svg = f'<svg width="100%" height="{total_h}" viewBox="0 0 {total_w} {total_h}" xmlns="http://www.w3.org/2000/svg">'
    svg += '''<defs><marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#95a5a6" /></marker></defs>'''
    svg += '''<style>
        .eaves {stroke: #2ecc71; stroke-width: 4;}   
        .rake {stroke: #f1c40f; stroke-width: 4;}    
        .ridge {stroke: #e74c3c; stroke-width: 4;}   
        .hip {stroke: #e74c3c; stroke-width: 3;}     
        .valley {stroke: #e67e22; stroke-width: 3;}
        .abutment {stroke: #3498db; stroke-width: 4;}
        .water {stroke: #95a5a6; stroke-width: 2; marker-end: url(#arrow); stroke-dasharray: 4 4;}
        .text {font-family: sans-serif; font-size: 13px; font-weight: bold; fill: #2c3e50;}
    </style>'''
    
    cx, cy = pad, pad

    if roof_type == 'shed':
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'      
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w}" y2="{cy}" class="abutment"/>'       
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+h}" class="rake"/>'           
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w}" y2="{cy+h}" class="rake"/>'       
        svg += f'<line x1="{cx+w/2}" y1="{cy+h*0.2}" x2="{cx+w/2}" y2="{cy+h*0.8}" class="water"/>'
        
    elif roof_type == 'gable':
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w}" y2="{cy}" class="eaves"/>'          
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'      
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+h}" class="rake"/>'           
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w}" y2="{cy+h}" class="rake"/>'       
        svg += f'<line x1="{cx}" y1="{cy+h/2}" x2="{cx+w}" y2="{cy+h/2}" class="ridge"/>'  
        svg += f'<line x1="{cx+w/2}" y1="{cy+h*0.3}" x2="{cx+w/2}" y2="{cy+h*0.1}" class="water"/>'
        svg += f'<line x1="{cx+w/2}" y1="{cy+h*0.7}" x2="{cx+w/2}" y2="{cy+h*0.9}" class="water"/>'

    elif roof_type == 'hip':
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w}" y2="{cy}" class="eaves"/>'          
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'      
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+h}" class="eaves"/>'           
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'       
        indent = (w - ridge_len * scale) / 2 if ridge_len > 0 else h / 2
        if indent < 0: indent = 0
        svg += f'<line x1="{cx+indent}" y1="{cy+h/2}" x2="{cx+w-indent}" y2="{cy+h/2}" class="ridge"/>'
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+indent}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+indent}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w-indent}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx+w}" y1="{cy+h}" x2="{cx+w-indent}" y2="{cy+h/2}" class="hip"/>'

    elif roof_type == 'tent':
        # Шатровая (все 4 угла сходятся в центр)
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w}" y2="{cy}" class="eaves"/>'          
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'      
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+h}" class="eaves"/>'           
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'       
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w/2}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w/2}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w/2}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx+w}" y1="{cy+h}" x2="{cx+w/2}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<circle cx="{cx+w/2}" cy="{cy+h/2}" r="5" fill="#e74c3c"/>' # Центр
        
        svg += f'<line x1="{cx+w/2}" y1="{cy+h*0.35}" x2="{cx+w/2}" y2="{cy+h*0.1}" class="water"/>'
        svg += f'<line x1="{cx+w/2}" y1="{cy+h*0.65}" x2="{cx+w/2}" y2="{cy+h*0.9}" class="water"/>'
        svg += f'<line x1="{cx+w*0.35}" y1="{cy+h/2}" x2="{cx+w*0.1}" y2="{cy+h/2}" class="water"/>'
        svg += f'<line x1="{cx+w*0.65}" y1="{cy+h/2}" x2="{cx+w*0.9}" y2="{cy+h/2}" class="water"/>'

    elif roof_type == 'multi_gable':
        # Многощипцовая (Крестовая)
        D = min(w, h) * 0.5 
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy}" x2="{cx+w/2+D/2}" y2="{cy}" class="rake"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy}" x2="{cx+w/2+D/2}" y2="{cy+h/2-D/2}" class="eaves"/>'
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy}" x2="{cx+w/2-D/2}" y2="{cy+h/2-D/2}" class="eaves"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy+h/2-D/2}" x2="{cx+w}" y2="{cy+h/2-D/2}" class="eaves"/>'
        svg += f'<line x1="{cx+w}" y1="{cy+h/2-D/2}" x2="{cx+w}" y2="{cy+h/2+D/2}" class="rake"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy+h/2+D/2}" x2="{cx+w}" y2="{cy+h/2+D/2}" class="eaves"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy+h/2+D/2}" x2="{cx+w/2+D/2}" y2="{cy+h}" class="eaves"/>'
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy+h}" x2="{cx+w/2+D/2}" y2="{cy+h}" class="rake"/>'
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy+h/2+D/2}" x2="{cx+w/2-D/2}" y2="{cy+h}" class="eaves"/>'
        svg += f'<line x1="{cx}" y1="{cy+h/2+D/2}" x2="{cx+w/2-D/2}" y2="{cy+h/2+D/2}" class="eaves"/>'
        svg += f'<line x1="{cx}" y1="{cy+h/2-D/2}" x2="{cx}" y2="{cy+h/2+D/2}" class="rake"/>'
        svg += f'<line x1="{cx}" y1="{cy+h/2-D/2}" x2="{cx+w/2-D/2}" y2="{cy+h/2-D/2}" class="eaves"/>'

        svg += f'<line x1="{cx+w/2}" y1="{cy}" x2="{cx+w/2}" y2="{cy+h}" class="ridge"/>'
        svg += f'<line x1="{cx}" y1="{cy+h/2}" x2="{cx+w}" y2="{cy+h/2}" class="ridge"/>'
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy+h/2-D/2}" x2="{cx+w/2}" y2="{cy+h/2}" class="valley"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy+h/2-D/2}" x2="{cx+w/2}" y2="{cy+h/2}" class="valley"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy+h/2+D/2}" x2="{cx+w/2}" y2="{cy+h/2}" class="valley"/>'
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy+h/2+D/2}" x2="{cx+w/2}" y2="{cy+h/2}" class="valley"/>'

    svg += f'<text x="{cx+w/2}" y="{cy-15}" text-anchor="middle" class="text">Длина / Ширина: {w_input} x {h_input} м</text>'
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
    if not user_message: return jsonify({"error": "Пустое сообщение"})
    formatted_contents = [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in chat_history]
    formatted_contents.append({"role": "user", "parts": [{"text": user_message}]})
    try:
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=formatted_contents,
            config=types.GenerateContentConfig(system_instruction="Ты профи-помощник по кровле."),
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))