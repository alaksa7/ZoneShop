from datetime import datetime, timedelta
import sqlite3
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)


def init_db():
  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            hwid TEXT PRIMARY KEY,
            expires_at TEXT
        )
    """)
  conn.commit()
  conn.close()


# HTML-шаблон простой панельки администратора
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Панель Выдачи Подписок</title>
    <style>
        body { font-family: Segoe UI, sans-serif; background: #181825; color: #CDD6F4; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1E1E2E; padding: 25px; border-radius: 12px; width: 350px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); text-align: center; }
        h2 { margin-top: 0; color: #89B4FA; }
        input, select, button { width: 100%; padding: 10px; margin: 8px 0; border-radius: 6px; border: 1px solid #313244; box-sizing: border-box; font-size: 14px; }
        input, select { background: #11111B; color: #CDD6F4; }
        button { background: #89B4FA; color: #11111B; font-weight: bold; border: none; cursor: pointer; }
        button:hover { background: #B4BEFE; }
        .msg { margin-top: 10px; font-weight: bold; color: #A6E3A1; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Выдача подписки</h2>
        <form method="POST" action="/admin">
            <input type="text" name="hwid" placeholder="Вставьте HWID..." required autocomplete="off">
            <select name="days">
                <option value="1">1 день</option>
                <option value="7">7 дней</option>
                <option value="30" selected>30 дней (1 месяц)</option>
                <option value="90">90 дней (3 месяца)</option>
                <option value="365">365 дней (1 год)</option>
            </select>
            <button type="submit">Выдать подписку</button>
        </form>
        {% if msg %}
            <div class="msg">{{ msg }}</div>
        {% endif %}
    </div>
</body>
</html>
"""


@app.route("/check", methods=["GET"])
def check_license():
  hwid = request.args.get("hwid")
  if not hwid:
    return jsonify({"active": False, "error": "No HWID provided"}), 400

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute("SELECT expires_at FROM licenses WHERE hwid = ?", (hwid,))
  row = cursor.fetchone()

  now = datetime.now()

  if not row:
    conn.close()
    return jsonify({"active": False, "error": "Подписка неактивна"})

  expires_at = datetime.fromisoformat(row[0])
  conn.close()

  if now < expires_at:
    return jsonify({"active": True, "expires_at": expires_at.isoformat()})
  else:
    return jsonify({"active": False, "error": "Срок подписки истёк"})


# Панель управления (открывается в браузере)
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
  msg = ""
  if request.method == "POST":
    hwid = request.form.get("hwid", "").strip()
    days = int(request.form.get("days", 30))

    if hwid:
      expires_at = datetime.now() + timedelta(days=days)
      conn = sqlite3.connect("database.db")
      cursor = conn.cursor()
      cursor.execute(
          """
            INSERT INTO licenses (hwid, expires_at) 
            VALUES (?, ?)
            ON CONFLICT(hwid) DO UPDATE SET expires_at=excluded.expires_at
        """,
          (hwid, expires_at.isoformat()),
      )
      conn.commit()
      conn.close()
      msg = f"Успешно! Доступ до {expires_at.strftime('%d.%m.%Y')}"

  return render_template_string(ADMIN_HTML, msg=msg)


if __name__ == "__main__":
  init_db()
  app.run(host="0.0.0.0", port=5000)