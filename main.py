from flask import Flask, render_template_string, request

app = Flask(__name__)

# HTML-шаблон прямо в коде (никаких отдельных файлов)
PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мой сайт на Python</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            text-align: center;
        }
        h1 { color: #333; margin-bottom: 10px; }
        p { color: #666; margin-bottom: 20px; line-height: 1.6; }
        input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            margin-bottom: 12px;
            outline: none;
            transition: border-color 0.3s;
        }
        input:focus { border-color: #667eea; }
        button {
            width: 100%;
            padding: 12px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover { background: #5568d3; }
        .result {
            margin-top: 20px;
            padding: 15px;
            background: #f0f4ff;
            border-radius: 10px;
            color: #333;
            font-weight: 500;
        }
        .footer { margin-top: 25px; font-size: 13px; color: #999; }
    </style>
</head>
<body>
    <div class="card">
        <h1>👋 Привет!</h1>
        <p>Это простой сайт на Python (Flask), задеплоенный на Vercel.</p>
        <form method="POST">
            <input type="text" name="name" placeholder="Введи своё имя..." required>
            <button type="submit">Поздороваться</button>
        </form>
        {% if greeting %}
            <div class="result">{{ greeting }}</div>
        {% endif %}
        <div class="footer">Работает на Python + Flask + Vercel</div>
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    greeting = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            greeting = f"Привет, {name}! 🎉"
    return render_template_string(PAGE, greeting=greeting)


# Для локального запуска (Vercel использует app как WSGI-приложение)
if __name__ == "__main__":
    app.run(debug=True)
