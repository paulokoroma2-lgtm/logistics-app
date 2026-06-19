import streamlit as st
import pandas as pd
import psycopg2
import bcrypt
from datetime import datetime, date

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Logistics Control Centre",
    page_icon="📦",
    layout="wide"
)

# =========================
# DB CONNECTION
# =========================
conn = psycopg2.connect(
    "postgresql://neondb_owner:npg_oDk2UqR3AtBl@ep-dark-bird-abr04jkk.eu-west-2.aws.neon.tech/neondb?sslmode=require"
)

c = conn.cursor()

# =========================
# SAFE SCHEMA INIT
# =========================
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    customer TEXT,
    order_number TEXT,
    carrier TEXT,
    tracking TEXT,
    status TEXT,
    expected_date TEXT
)
""")

conn.commit()

# =========================
# SAFE ADMIN SEED (ONLY IF CLEAN DB)
# =========================
c.execute("SELECT id FROM users WHERE username=%s", ("admin",))
if not c.fetchone():
    hashed = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt())
    c.execute(
        "INSERT INTO users (username, password) VALUES (%s, %s)",
        ("admin", hashed.decode("utf-8"))
    )
    conn.commit()

# =========================
# SESSION STATE
# =========================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# =========================
# AUTH SCREEN
# =========================
if st.session_state.user_id is None:

    st.title("📦 Logistics Control Centre")

    tab1, tab2 = st.tabs(["Login", "Create Account"])

    # ---------------- LOGIN ----------------
    with tab1:

        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login"):

            c.execute("""
                SELECT id, password FROM users
                WHERE username=%s
            """, (username.strip(),))

            user = c.fetchone()

            if user:

                user_id = user[0]
                stored_hash = user[1]

                # ---- FIX ALL BCRYPT EDGE CASES ----
                try:
                    if isinstance(stored_hash, str):
                        stored_hash = stored_hash.encode("utf-8")

                    if bcrypt.checkpw(
                        password.strip().encode("utf-8"),
                        stored_hash
                    ):
                        st.session_state.user_id = user_id
                        st.rerun()
                    else:
                        st.error("Invalid credentials")

                except Exception:
                    st.error("Corrupted password data detected. Please reset user or re-register.")

            else:
                st.error("Invalid credentials")

    # ---------------- SIGNUP ----------------
    with tab2:

        new_user = st.text_input("New Username", key="signup_user")
        new_pass = st.text_input("New Password", type="password", key="signup_pass")

        if st.button("Create Account"):

            hashed_pw = bcrypt.hashpw(
                new_pass.strip().encode("utf-8"),
                bcrypt.gensalt()
            )

            try:
                c.execute("""
                    INSERT INTO users (username, password)
                    VALUES (%s, %s)
                """, (new_user.strip(), hashed_pw.decode("utf-8")))

                conn.commit()
                st.success("Account created — you can now log in")

            except:
                st.error("Username already exists")

    st.stop()

# =========================
# DATA LOADING
# =========================
def load_data(user_id):
    return pd.read_sql_query(
        "SELECT * FROM orders WHERE user_id = %s",
        conn,
        params=(user_id,)
    )

# =========================
# STATUS ENGINE
# =========================
def compute_status(status, expected_date):

    status = (status or "").lower()

    if status == "delivered":
        return "🟢 Delivered"

    try:
        expected = datetime.strptime(str(expected_date), "%Y-%m-%d").date()

        if expected < date.today():
            return "🔴 Delayed"

        return "🔵 In Transit"

    except:
        return "⚪ Unknown"

# =========================
# LOAD USER DATA
# =========================
df = load_data(st.session_state.user_id)

# =========================
# HEADER
# =========================
st.title("📦 Logistics Control Centre")

if st.sidebar.button("Logout"):
    st.session_state.user_id = None
    st.rerun()

page = st.sidebar.radio("Navigation", ["Orders", "Add Order", "Analytics"])

# =========================
# ORDERS
# =========================
if page == "Orders":

    st.subheader("Orders")

    if df.empty:
        st.info("No orders found")
    else:
        for _, row in df.iterrows():

            st.markdown(f"""
            <div style="
                background:#111827;
                padding:16px;
                border-radius:12px;
                border:1px solid #1f2937;
                margin-bottom:12px;
                color:white;
            ">
                <h4>Order #{row['order_number']}</h4>
                <b>Customer:</b> {row['customer']}<br>
                <b>Carrier:</b> {row['carrier']}<br>
                <b>Tracking:</b> {row['tracking']}<br>
                <b>Status:</b> {compute_status(row['status'], row['expected_date'])}<br>
                <b>Expected:</b> {row['expected_date']}
            </div>
            """, unsafe_allow_html=True)

# =========================
# ADD ORDER
# =========================
elif page == "Add Order":

    st.subheader("Create Order")

    customer = st.text_input("Customer Name")
    order_number = st.text_input("Order Number")
    carrier = st.selectbox("Carrier", ["DHL", "UPS", "Royal Mail", "FedEx"])
    tracking = st.text_input("Tracking Number")
    status = st.selectbox("Status", ["Pending", "Shipped", "Delivered", "Late"])
    expected_date = st.date_input("Expected Delivery Date")

    if st.button("Create Order"):

        c.execute("""
            INSERT INTO orders (
                user_id,
                customer,
                order_number,
                carrier,
                tracking,
                status,
                expected_date
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            st.session_state.user_id,
            customer,
            order_number,
            carrier,
            tracking,
            status,
            str(expected_date)
        ))

        conn.commit()
        st.success("Order created")
        st.rerun()

# =========================
# ANALYTICS
# =========================
elif page == "Analytics":

    st.subheader("Analytics")

    if not df.empty:
        st.bar_chart(df["carrier"].value_counts())
        st.bar_chart(df["status"].value_counts())
    else:
        st.info("No data available")