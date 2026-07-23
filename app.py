from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3, os

app = Flask(__name__)
app.secret_key = "dev-key-2025"

# ── 文件上传配置 ──
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
os.makedirs(UPLOAD_DIR, exist_ok=True)

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "users.db")


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            phone TEXT
        )
    """)
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)",
              ("admin", "admin123", "admin@example.com", "13800138000"))
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone) VALUES (?, ?, ?, ?)",
              ("alice", "alice2025", "alice@example.com", "13900139001"))

    # 添加余额字段（兼容已有数据库）
    try:
        c.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
        print("[数据库] 添加 balance 字段")
    except sqlite3.OperationalError:
        pass  # 字段已存在

    # 添加头像字段（兼容已有数据库）
    try:
        c.execute("ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT ''")
        print("[数据库] 添加 avatar 字段")
    except sqlite3.OperationalError:
        pass  # 字段已存在

    # 为用户设置默认余额
    c.execute("UPDATE users SET balance = 99999 WHERE username = 'admin' AND (balance IS NULL OR balance = 0)")
    c.execute("UPDATE users SET balance = 100 WHERE username = 'alice' AND (balance IS NULL OR balance = 0)")

    conn.commit()
    conn.close()
    print("[数据库] 初始化完成")


def get_user_by_username(username):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None


init_db()


@app.route("/")
def index():
    username = session.get("username")
    user = None
    keyword = request.args.get("keyword", "")
    results = None

    if username:
        user = get_user_by_username(username)

    # 搜索功能
    if keyword:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        sql = f"SELECT * FROM users WHERE username LIKE '%{keyword}%' OR email LIKE '%{keyword}%'"
        print(f"[搜索] 执行 SQL: {sql}")
        c.execute(sql)
        rows = c.fetchall()
        results = [dict(r) for r in rows]
        conn.close()

    return render_template("index.html", user=user, results=results, keyword=keyword)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    success = request.args.get("success", "")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_username(username)
        if user and user["password"] == password:
            session["username"] = username
            session["avatar"] = user.get("avatar", "")
            return redirect("/")
        else:
            error = "用户名或密码错误"

    return render_template("login.html", error=error, success=success)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        if not username or not password:
            error = "用户名和密码不能为空"
        else:
            try:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                sql = f"INSERT INTO users (username, password, email, phone) VALUES ('{username}', '{password}', '{email}', '{phone}')"
                print(f"[注册] 执行 SQL: {sql}")
                c.execute(sql)
                conn.commit()
                conn.close()
                return redirect("/login?success=注册成功，请登录")
            except Exception as e:
                error = f"注册失败：{str(e)}"

    return render_template("register.html", error=error)


@app.route("/search")
def search():
    keyword = request.args.get("keyword", "")
    return redirect(f"/?keyword={keyword}")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "username" not in session:
        return redirect("/login")

    file_url = None
    error = None

    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename:
            filename = file.filename
            save_path = os.path.join(UPLOAD_DIR, filename)
            file.save(save_path)
            file_url = url_for("static", filename=f"uploads/{filename}")

            # 将头像路径保存到当前登录用户的数据库记录
            username = session["username"]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE users SET avatar = ? WHERE username = ?", (file_url, username))
            conn.commit()
            conn.close()
            # 刷新 session 中的头像
            session["avatar"] = file_url
        else:
            error = "请选择一个文件"

    return render_template("upload.html", file_url=file_url, error=error)


@app.route("/page")
def dynamic_page():
    name = request.args.get("name", "")
    page_content = None
    page_error = None

    if name:
        # 直接拼接用户输入的 name 到路径，不校验 ../，不规范化路径
        pages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
        file_path = os.path.join(pages_dir, name)

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                page_content = f.read()
        else:
            # 尝试加上 .html 后缀
            file_path_html = file_path + ".html"
            if os.path.exists(file_path_html):
                with open(file_path_html, "r", encoding="utf-8") as f:
                    page_content = f.read()
            else:
                page_error = "页面不存在"
    else:
        page_error = "请提供页面名称"

    # 将 page_content 传给首页渲染
    username = session.get("username")
    user = None
    keyword = ""
    results = None
    if username:
        user = get_user_by_username(username)

    return render_template("index.html", user=user, results=results, keyword=keyword,
                           page_content=page_content, page_error=page_error)


@app.route("/profile")
def profile():
    user_id = request.args.get("user_id", type=int)
    user = None
    error = None

    if user_id:
        user = get_user_by_id(user_id)
        if not user:
            error = f"未找到 ID 为 {user_id} 的用户"
    else:
        error = "请提供 user_id 参数"

    return render_template("profile.html", user=user, error=error)


@app.route("/recharge", methods=["POST"])
def recharge():
    user_id = request.form.get("user_id", type=int)
    amount = request.form.get("amount", type=float, default=0)

    if user_id:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
        conn.commit()
        conn.close()

    return redirect(f"/profile?user_id={user_id}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
