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

# ТВОЙ КЛЮЧ (убедись, что он в переменных окружения)
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
    Выведи ответ списком и определи тип кровли.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=[prompt, img]
        )
        return jsonify({"result": response.text})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/generate_scheme", methods=["POST"])
def generate_scheme():
    data = request.json
    roof_type = data.get("roof_type", "shed")

    w_in = float(data.get("width", 0))
    h_in = float(data.get("height", 0))
    s_trap = float(data.get("slope_trap", 0))
    s_hip = float(data.get("slope_hip", 0))
    r_len = float(data.get("ridge", 0))
    h_len = float(data.get("hip", 0))

    if w_in <= 0 or h_in <= 0:
        return jsonify({"svg": "<p style='color:red;'>Укажите размеры больше 0.</p>"})

    scale = 350 / max(w_in, h_in)
    w, h = w_in * scale, h_in * scale
    pad = 100
    tw, th = w + pad * 2, h + pad * 2

    svg = f'<svg width="100%" height="{th}" viewBox="0 0 {tw} {th}" xmlns="http://www.w3.org/2000/svg">'
    svg += """<defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#95a5a6" />
        </marker>
    </defs>"""

    svg += """<style>
        .eaves {stroke: #2ecc71; stroke-width: 4;}   
        .rake {stroke: #f1c40f; stroke-width: 4;}    
        .ridge {stroke: #e74c3c; stroke-width: 4;}   
        .hip {stroke: #e74c3c; stroke-width: 3;}     
        .valley {stroke: #e67e22; stroke-width: 3;}
        .abut {stroke: #3498db; stroke-width: 4;}
        .water {stroke: #95a5a6; stroke-width: 2; marker-end: url(#arrow); stroke-dasharray: 4 4;}
        .txt {font-family: sans-serif; font-size: 13px; font-weight: bold; fill: #2c3e50;}
        .txt-r {font-family: sans-serif; font-size: 13px; font-weight: bold; fill: #c0392b;}
    </style>"""

    cx, cy = pad, pad

    if roof_type == "shed":
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w}" y2="{cy}" class="abut"/>'
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+h}" class="rake"/>'
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w}" y2="{cy+h}" class="rake"/>'
        svg += f'<line x1="{cx+w/2}" y1="{cy+h*0.2}" x2="{cx+w/2}" y2="{cy+h*0.8}" class="water"/>'
        svg += f'<text x="{cx+w/2}" y="{cy-10}" text-anchor="middle" class="txt">Примыкание: {w_in}м</text>'
        svg += f'<text x="{cx+w/2}" y="{cy+h+20}" text-anchor="middle" class="txt">Карниз: {w_in}м</text>'
        svg += f'<text x="{cx-10}" y="{cy+h/2}" text-anchor="middle" transform="rotate(-90,{cx-10},{cy+h/2})" class="txt">Торец (скат): {s_trap}м</text>'

    elif roof_type == "gable":
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w}" y2="{cy}" class="eaves"/>'
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w}" y2="{cy+h}" class="eaves"/>'
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy+h}" class="rake"/>'
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w}" y2="{cy+h}" class="rake"/>'
        svg += (
            f'<line x1="{cx}" y1="{cy+h/2}" x2="{cx+w}" y2="{cy+h/2}" class="ridge"/>'
        )
        svg += f'<line x1="{cx+w/2}" y1="{cy+h/2-10}" x2="{cx+w/2}" y2="{cy+10}" class="water"/>'
        svg += f'<line x1="{cx+w/2}" y1="{cy+h/2+10}" x2="{cx+w/2}" y2="{cy+h-10}" class="water"/>'
        svg += f'<text x="{cx+w/2}" y="{cy-10}" text-anchor="middle" class="txt">Карниз: {w_in}м</text>'
        svg += f'<text x="{cx+w/2}" y="{cy+h+20}" text-anchor="middle" class="txt">Карниз: {w_in}м</text>'
        svg += f'<text x="{cx+w/2}" y="{cy+h/2-7}" text-anchor="middle" class="txt-r">Конёк: {r_len}м</text>'
        svg += f'<text x="{cx-10}" y="{cy+h/4}" text-anchor="middle" transform="rotate(-90,{cx-10},{cy+h/4})" class="txt">Торец: {s_trap}м</text>'

    elif roof_type == "hip":
        svg += f'<rect x="{cx}" y="{cy}" width="{w}" height="{h}" fill="none" class="eaves"/>'
        indent = (w - r_len * scale) / 2
        svg += f'<line x1="{cx+indent}" y1="{cy+h/2}" x2="{cx+w-indent}" y2="{cy+h/2}" class="ridge"/>'
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+indent}" y2="{cy+h/2}" class="hip"/>'
        svg += (
            f'<line x1="{cx}" y1="{cy+h}" x2="{cx+indent}" y2="{cy+h/2}" class="hip"/>'
        )
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w-indent}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx+w}" y1="{cy+h}" x2="{cx+w-indent}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx+w/2}" y1="{cy+h/2-10}" x2="{cx+w/2}" y2="{cy+10}" class="water"/>'
        svg += f'<line x1="{cx+w/2}" y1="{cy+h/2+10}" x2="{cx+w/2}" y2="{cy+h-10}" class="water"/>'
        svg += f'<line x1="{cx+indent/2}" y1="{cy+h/2}" x2="{cx+15}" y2="{cy+h/2}" class="water"/>'
        svg += f'<line x1="{cx+w-indent/2}" y1="{cy+h/2}" x2="{cx+w-15}" y2="{cy+h/2}" class="water"/>'
        svg += f'<text x="{cx+w/2}" y="{cy-10}" text-anchor="middle" class="txt">Карниз: {w_in}м | Скат: {s_trap}м</text>'
        svg += f'<text x="{cx-10}" y="{cy+h/2}" text-anchor="middle" transform="rotate(-90,{cx-10},{cy+h/2})" class="txt">Карниз: {h_in}м | Скат: {s_hip}м</text>'
        svg += f'<text x="{cx+w/2}" y="{cy+h/2-7}" text-anchor="middle" class="txt-r">Конёк: {r_len}м</text>'
        svg += f'<text x="{cx+indent/2}" y="{cy+h/4}" text-anchor="middle" class="txt-r">Хребет: {h_len}м</text>'

    elif roof_type == "tent":
        svg += f'<rect x="{cx}" y="{cy}" width="{w}" height="{h}" fill="none" class="eaves"/>'
        svg += f'<line x1="{cx}" y1="{cy}" x2="{cx+w/2}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx+w}" y1="{cy}" x2="{cx+w/2}" y2="{cy+h/2}" class="hip"/>'
        svg += f'<line x1="{cx}" y1="{cy+h}" x2="{cx+w/2}" y2="{cy+h/2}" class="hip"/>'
        svg += (
            f'<line x1="{cx+w}" y1="{cy+h}" x2="{cx+w/2}" y2="{cy+h/2}" class="hip"/>'
        )
        svg += f'<line x1="{cx+w/2}" y1="{cy+h/2-15}" x2="{cx+w/2}" y2="{cy+10}" class="water"/>'
        svg += f'<line x1="{cx+w/2}" y1="{cy+h/2+15}" x2="{cx+w/2}" y2="{cy+h-10}" class="water"/>'
        svg += f'<line x1="{cx+w/4}" y1="{cy+h/2}" x2="{cx+15}" y2="{cy+h/2}" class="water"/>'
        svg += f'<line x1="{cx+w*0.75}" y1="{cy+h/2}" x2="{cx+w-15}" y2="{cy+h/2}" class="water"/>'
        svg += f'<text x="{cx+w/2}" y="{cy-10}" text-anchor="middle" class="txt">Карниз: {w_in}м | Скат: {s_trap}м</text>'
        svg += f'<text x="{cx+w/4}" y="{cy+h/4}" text-anchor="middle" class="txt-r">Хребет: {h_len}м</text>'

    elif roof_type == "multi_gable":
        D = min(w, h) * 0.5

        # 1. Линии контура (Карнизы - зеленые, Торцы - желтые)
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy}" x2="{cx+w/2+D/2}" y2="{cy}" class="rake"/>'
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy}" x2="{cx+w/2-D/2}" y2="{cy+h/2-D/2}" class="eaves"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy}" x2="{cx+w/2+D/2}" y2="{cy+h/2-D/2}" class="eaves"/>'

        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy+h/2-D/2}" x2="{cx+w}" y2="{cy+h/2-D/2}" class="eaves"/>'
        svg += f'<line x1="{cx+w}" y1="{cy+h/2-D/2}" x2="{cx+w}" y2="{cy+h/2+D/2}" class="rake"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy+h/2+D/2}" x2="{cx+w}" y2="{cy+h/2+D/2}" class="eaves"/>'

        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy+h/2+D/2}" x2="{cx+w/2-D/2}" y2="{cy+h}" class="eaves"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy+h/2+D/2}" x2="{cx+w/2+D/2}" y2="{cy+h}" class="eaves"/>'
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy+h}" x2="{cx+w/2+D/2}" y2="{cy+h}" class="rake"/>'

        svg += f'<line x1="{cx}" y1="{cy+h/2-D/2}" x2="{cx+w/2-D/2}" y2="{cy+h/2-D/2}" class="eaves"/>'
        svg += f'<line x1="{cx}" y1="{cy+h/2-D/2}" x2="{cx}" y2="{cy+h/2+D/2}" class="rake"/>'
        svg += f'<line x1="{cx}" y1="{cy+h/2+D/2}" x2="{cx+w/2-D/2}" y2="{cy+h/2+D/2}" class="eaves"/>'

        # 2. Коньки (Красные)
        svg += (
            f'<line x1="{cx+w/2}" y1="{cy}" x2="{cx+w/2}" y2="{cy+h}" class="ridge"/>'
        )
        svg += (
            f'<line x1="{cx}" y1="{cy+h/2}" x2="{cx+w}" y2="{cy+h/2}" class="ridge"/>'
        )

        # 3. Ендовы (Оранжевые)
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy+h/2-D/2}" x2="{cx+w/2}" y2="{cy+h/2}" class="valley"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy+h/2-D/2}" x2="{cx+w/2}" y2="{cy+h/2}" class="valley"/>'
        svg += f'<line x1="{cx+w/2+D/2}" y1="{cy+h/2+D/2}" x2="{cx+w/2}" y2="{cy+h/2}" class="valley"/>'
        svg += f'<line x1="{cx+w/2-D/2}" y1="{cy+h/2+D/2}" x2="{cx+w/2}" y2="{cy+h/2}" class="valley"/>'

        # 4. Стрелки ската воды (по всем 8 направлениям)
        svg += f'<line x1="{cx+w/4}" y1="{cy+h/2-5}" x2="{cx+w/4}" y2="{cy+h/2-D/2+15}" class="water"/>'
        svg += f'<line x1="{cx+w/4}" y1="{cy+h/2+5}" x2="{cx+w/4}" y2="{cy+h/2+D/2-15}" class="water"/>'
        svg += f'<line x1="{cx+w*0.75}" y1="{cy+h/2-5}" x2="{cx+w*0.75}" y2="{cy+h/2-D/2+15}" class="water"/>'
        svg += f'<line x1="{cx+w*0.75}" y1="{cy+h/2+5}" x2="{cx+w*0.75}" y2="{cy+h/2+D/2-15}" class="water"/>'
        svg += f'<line x1="{cx+w/2-5}" y1="{cy+h/4}" x2="{cx+w/2-D/2+15}" y2="{cy+h/4}" class="water"/>'
        svg += f'<line x1="{cx+w/2+5}" y1="{cy+h/4}" x2="{cx+w/2+D/2-15}" y2="{cy+h/4}" class="water"/>'
        svg += f'<line x1="{cx+w/2-5}" y1="{cy+h*0.75}" x2="{cx+w/2-D/2+15}" y2="{cy+h*0.75}" class="water"/>'
        svg += f'<line x1="{cx+w/2+5}" y1="{cy+h*0.75}" x2="{cx+w/2+D/2-15}" y2="{cy+h*0.75}" class="water"/>'

        # 5. Подписи текстом (как на твоем рисунке)
        svg += f'<text x="{cx-10}" y="{cy+h/2}" text-anchor="middle" transform="rotate(-90,{cx-10},{cy+h/2})" class="txt">Торец</text>'

        # <--- ВОТ ИСПРАВЛЕННАЯ СТРОКА: ТЕКСТ СМЕЩЕН В УГОЛ И В СТОРОНУ (на 25 влево и на 15 вниз) --->
        svg += f'<text x="{cx+w/2-D/2-25}" y="{cy+h/2-D/2+15}" text-anchor="middle" class="txt">Карниз</text>'

        svg += f'<text x="{cx+w*0.75}" y="{cy+h/2-5}" text-anchor="middle" class="txt-r">Конек</text>'
        svg += f'<text x="{cx+w/2-D/4-10}" y="{cy+h/2+D/4+15}" text-anchor="middle" class="txt" style="fill:#e67e22;">Ендова</text>'
        svg += f'<text x="{cx+w/2}" y="{cy+h+25}" text-anchor="middle" class="txt">Длина: {w_in}м | Ширина: {h_in}м | Скат: {s_trap}м</text>'

    svg += "</svg>"

    legend = """
    <div style="margin-top: 10px; display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; font-size: 14px; font-weight: bold; background: #fdfefe; padding: 10px; border-radius: 5px; border: 1px solid #eee;">
       <div><span style="color: #2ecc71; font-size: 18px;">■</span> Карниз</div>
       <div><span style="color: #f1c40f; font-size: 18px;">■</span> Торец</div>
       <div><span style="color: #e74c3c; font-size: 18px;">■</span> Конек/Хребет</div>
       <div><span style="color: #e67e22; font-size: 18px;">■</span> Ендова</div>
       <div><span style="color: #3498db; font-size: 18px;">■</span> Примыкание</div>
    </div>
    """
    return jsonify({"svg": svg + legend})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
