from flask import Flask, render_template, redirect, url_for, session, request
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = "cineplexx_secret_key"  # change later

# ---------------------------
# POSTGRESQL CONFIG
# ---------------------------

DB_CONFIG = {
    "host": "localhost",
    "dbname": "cineplexx",
    "user": "postgres",
    "password": "myfuture_1692"
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


# ---------------------------
# CONSTANTS
# ---------------------------

USER_ID_START = 1028


# ---------------------------
# INIT SESSION USER
# ---------------------------

def init_user():
    session.setdefault("logged_in", False)
    session.setdefault("reward_claimed", False)
    session.setdefault("activity", [])


# ---------------------------
# LOGIN PAGE
# ---------------------------

@app.route("/", methods=["GET", "POST"])
def login():
    init_user()
    error = None

    if request.method == "POST":
        phone = request.form.get("phone")
        password = request.form.get("password")

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        cur.execute(
            "SELECT * FROM users WHERE phone = %s",
            (phone,)
        )
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and user["password"] == password:
            session["logged_in"] = True
            session["user_id"] = user["user_id"]
            session["reward_claimed"] = user["reward_claimed"]

            if not session["reward_claimed"]:
                return redirect(url_for("reward"))

            return redirect(url_for("movies"))
        else:
            error = "Invalid phone number or password"

    return render_template("login.html", error=error)


# ---------------------------
# REGISTER PAGE
# ---------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        referral = request.form.get("referral")

        # 🔹 Capture registration IP address
        registration_ip = request.headers.get(
            "X-Forwarded-For",
            request.remote_addr
        )

        if not phone or not password or not confirm or not referral:
            error = "All fields are required"
        elif password != confirm:
            error = "Passwords do not match"
        else:
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                "SELECT 1 FROM users WHERE phone = %s",
                (phone,)
            )

            if cur.fetchone():
                error = "Phone number already exists"
            else:
                cur.execute("SELECT COUNT(*) FROM users")
                count = cur.fetchone()[0]

                user_id = USER_ID_START + count + 1

                cur.execute(
                    """
                    INSERT INTO users (
                        phone,
                        password,
                        referral,
                        reward_claimed,
                        user_id,
                        registration_ip
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (phone, password, referral, False, user_id, registration_ip)
                )

                conn.commit()
                cur.close()
                conn.close()

                return redirect(url_for("login"))

            cur.close()
            conn.close()

    return render_template("register.html", error=error)


# ---------------------------
# 100€ REWARD (ONLY ONCE)
# ---------------------------

@app.route("/reward", methods=["GET", "POST"])
def reward():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if session["reward_claimed"]:
        return redirect(url_for("movies"))

    if request.method == "POST":
        session["reward_claimed"] = True
        session["activity"].append("100€ initial worker reward claimed")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET reward_claimed = TRUE
            WHERE user_id = %s
            """,
            (session["user_id"],)
        )

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("movies"))

    return render_template("reward.html")


# ---------------------------
# MOVIES PAGE
# ---------------------------

@app.route("/movies")
def movies():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return render_template("movies.html")


@app.route("/more")
def more():
    if not session.get("logged_in"):
        return render_template("movies.html")

    return render_template("more.html", user_id=session["user_id"])


# ---------------------------
# ACTIVITY / NOTIFICATIONS
# ---------------------------

@app.route("/activity")
def activity():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return render_template(
        "activity.html",
        notifications=session["activity"]
    )


# ---------------------------
# ABOUT PAGE
# ---------------------------

@app.route("/about")
def about():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return render_template("about.html")


# ---------------------------
# RUN APP
# ---------------------------

if __name__ == "__main__":
    app.run(debug=True)
