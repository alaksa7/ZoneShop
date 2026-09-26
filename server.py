from datetime import datetime, timedelta
import sqlite3
from flask import (Flask, jsonify, request, render_template_string,
                   redirect, url_for)

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


ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Панель управления подписками</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #181825;
            color: #CDD6F4;
            margin: 0;
            padding: 30px 15px;
            min-height: 100vh;
        }
        .container { max-width: 900px; margin: 0 auto; }

        .card {
            background: #1E1E2E;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            margin-bottom: 20px;
        }

        h2 { margin-top: 0; color: #89B4FA; }
        h3 { color: #89B4FA; font-size: 16px; margin: 0 0 15px 0; }
        .count { color: #6C7086; font-weight: normal; font-size: 14px; }

        input, select, button {
            padding: 10px;
            margin: 8px 0;
            border-radius: 6px;
            border: 1px solid #313244;
            font-size: 14px;
            font-family: inherit;
        }
        input, select { background: #11111B; color: #CDD6F4; width: 100%; }
        button {
            background: #89B4FA;
            color: #11111B;
            font-weight: bold;
            border: none;
            cursor: pointer;
            width: 100%;
        }
        button:hover { background: #B4BEFE; }

        .msg {
            padding: 12px 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            font-weight: bold;
        }
        .msg-ok  { background: #1e3a2f; color: #A6E3A1; border-left: 4px solid #A6E3A1; }
        .msg-err { background: #3a1e2a; color: #F38BA8; border-left: 4px solid #F38BA8; }

        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th {
            color: #89B4FA;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 10px 8px;
            text-align: left;
            border-bottom: 2px solid #313244;
        }
        td {
            padding: 12px 8px;
            border-bottom: 1px solid #313244;
            font-size: 14px;
        }
        tr:hover { background: #252535; }

        .hwid { font-family: 'Consolas', monospace; font-size: 12px; word-break: break-all; }
        .active  { color: #A6E3A1; }
        .expired { color: #F38BA8; }

        .revoke-btn {
            background: #F38BA8;
            color: #11111B;
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            font-size: 12px;
            width: auto;
            margin: 0;
        }
        .revoke-btn:hover { background: #EBA0B8; }

        .empty { text-align: center; padding: 30px; color: #6C7086; }
    </style>
</head>
<body>
    <div class="container">
        {% if msg %}
            <div class="msg msg-{{ msg_type }}">{{ msg }}</div>
        {% endif %}

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
        </div>

        <div class="card">
            <h3>Все подписки <span class="count">({{ count }})</span></h3>
            {% if subs %}
            <table>
                <thead>
                    <tr>
                        <th>HWID</th>
                        <th>Истекает</th>
                        <th>Статус</th>
                        <th style="text-align: right;">Действие</th>
                    </tr>
                </thead>
                <tbody>
                    {% for s in subs %}
                    <tr>
                        <td class="hwid">{{ s.hwid }}</td>
                        <td>{{ s.expires }}</td>
                        <td>
                            {% if s.active %}
                                <span class="active">● Активна</span>
                            {% else %}
                                <span class="expired">● Истекла</span>
                            {% endif %}
                        </td>
                        <td style="text-align: right;">
                            <form method="POST" action="/admin/revoke"
                                  onsubmit="return confirm('Удалить подписку у {{ s.hwid }}?');"
                                  style="display: inline;">
                                <input type="hidden" name="hwid" value="{{ s.hwid }}">
                                <button type="submit" class="revoke-btn">Удалить</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
                <div class="empty">Пока нет ни одной подписки</div>
            {% endif %}
        </div>
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


@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    msg = request.args.get("msg", "")
    msg_type = request.args.get("type", "ok")

    # --- Выдача подписки ---
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
            return redirect(url_for(
                "admin_panel",
                msg=f"Выдано до {expires_at.strftime('%d.%m.%Y')}",
                type="ok",
            ))

    # --- Список всех подписок ---
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT hwid, expires_at FROM licenses ORDER BY expires_at DESC")
    rows = cursor.fetchall()
    conn.close()

    now = datetime.now()
    subs = []
    for hwid, exp_iso in rows:
        try:
            exp = datetime.fromisoformat(exp_iso)
            is_active = now < exp
            exp_str = exp.strftime("%d.%m.%Y")
        except Exception:
            exp_str = "—"
            is_active = False
        subs.append({
            "hwid": hwid,
            "expires": exp_str,
            "active": is_active,
        })

    return render_template_string(
        ADMIN_HTML,
        msg=msg,
        msg_type=msg_type,
        subs=subs,
        count=len(subs),
    )


@app.route("/admin/revoke", methods=["POST"])
def admin_revoke():
    hwid = request.form.get("hwid", "").strip()
    if not hwid:
        return redirect(url_for("admin_panel", msg="HWID не указан", type="err"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM licenses WHERE hwid = ?", (hwid,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted:
        short = hwid[:16] + ("..." if len(hwid) > 16 else "")
        return redirect(url_for(
            "admin_panel",
            msg=f"Подписка {short} удалена",
            type="err",
        ))
    else:
        return redirect(url_for("admin_panel", msg="HWID не найден", type="err"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)