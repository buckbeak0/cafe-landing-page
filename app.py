import sqlite3
from datetime import datetime, timedelta
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

app = Flask(__name__)
app.secret_key = "dlsjaflkasjf"  

DB_NAME = "cafe.db"
RESERVATION_GAP = timedelta(hours=3)
MAX_DAYS_AHEAD = 2

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "coffee123"  


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            table_no INTEGER,
            res_time TEXT,
            pno INTEGER,
            email TEXT
        );
    """)
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/reserve_table", methods=["GET", "POST"])
def reserve_table():
    if request.method == "POST":
        table_id = request.form.get("table_id")
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()
        res_time_raw = (request.form.get("arrival_time") or "").strip()

        if not table_id:
            flash("Please select a table!")
            return redirect(url_for("reserve_table"))

        if not name:
            flash("Please enter your name!")
            return redirect(url_for("reserve_table"))

        if not (phone or email):
            flash("Provide at least phone or email!")
            return redirect(url_for("reserve_table"))

        try:
            res_time = datetime.fromisoformat(res_time_raw)
        except Exception:
            flash("Invalid date and time.")
            return redirect(url_for("reserve_table"))

        now = datetime.now()
        if res_time < now:
            flash("Choose a future time!")
            return redirect(url_for("reserve_table"))

        if res_time > now + timedelta(days=MAX_DAYS_AHEAD):
            flash("Reservations allowed only 2 days ahead!")
            return redirect(url_for("reserve_table"))

        # check time conflicts (3-hour gap on same table)
        conn = get_db()
        rows = conn.execute(
            "SELECT res_time FROM reservations WHERE table_no = ?",
            (table_id,),
        ).fetchall()

        for r in rows:
            existing = datetime.fromisoformat(r["res_time"])
            if abs(existing - res_time) < RESERVATION_GAP:
                flash(
                    "This table already has a reservation within 3 hours "
                    "of that time. Choose another slot or table."
                )
                conn.close()
                return redirect(
                    url_for("reserve_table", arrival_time=res_time_raw)
                )

        # insert reservation
        conn.execute(
            "INSERT INTO reservations (name, table_no, res_time, pno, email) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, table_id, res_time_raw, phone, email),
        )
        conn.commit()
        conn.close()

        flash("Reservation successful!")
        return redirect(url_for("home"))

    # ---------- GET ----------
    arrival_raw = (request.args.get("arrival_time") or "").strip()
    reserved_tables = set()

    if arrival_raw:
        try:
            chosen_time = datetime.fromisoformat(arrival_raw)
            conn = get_db()
            rows = conn.execute(
                "SELECT table_no, res_time FROM reservations"
            ).fetchall()
            conn.close()

            for r in rows:
                existing = datetime.fromisoformat(r["res_time"])
                if abs(existing - chosen_time) < RESERVATION_GAP:
                    reserved_tables.add(str(r["table_no"]))
        except Exception:
            pass

    return render_template(
        "reserve_table.html",
        reserved_tables=list(reserved_tables),
        arrival_time_value=arrival_raw,
    )


def is_admin_logged_in():
    return session.get("admin_logged_in") is True


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash("Logged in as admin.")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials.")
            return redirect(url_for("admin_login"))

    # GET
    if is_admin_logged_in():
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Logged out.")
    return redirect(url_for("home"))


@app.route("/admin")
def admin_dashboard():
    if not is_admin_logged_in():
        flash("Please log in as admin to access that page.")
        return redirect(url_for("admin_login"))

    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, table_no, res_time, pno, email "
        "FROM reservations ORDER BY res_time ASC"
    ).fetchall()
    conn.close()

    return render_template("admin_dashboard.html", reservations=rows)


@app.post("/admin/delete/<int:res_id>")
def admin_delete_reservation(res_id):
    if not is_admin_logged_in():
        flash("Not authorized.")
        return redirect(url_for("admin_login"))

    conn = get_db()
    conn.execute("DELETE FROM reservations WHERE id = ?", (res_id,))
    conn.commit()
    conn.close()

    flash(f"Reservation #{res_id} deleted.")
    return redirect(url_for("admin_dashboard"))


@app.route("/debug/reservations")
def debug_reservations():
    conn = get_db()
    rows = conn.execute("SELECT * FROM reservations").fetchall()
    conn.close()

    html = "<h2>Reservations</h2>"
    for r in rows:
        html += (
            f"{r['id']} | Table {r['table_no']} | {r['name']} | "
            f"{r['res_time']} | {r['pno']} | {r['email']}<br>"
        )
    return html or "None"


if __name__ == "__main__":
    app.run(debug=True)
