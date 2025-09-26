import streamlit as st

# --- Simple Password Protection ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "1907":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don’t store it
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Wrong password
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("🔒 Incorrect password")
        return False
    else:
        return True

# --- Your app content ---
if check_password():
    st.title("Profit Margin Summary App")
    st.write("✅ Welcome, you are logged in!")
    # put the rest of your app code here (UI, uploads, etc.)



import os
from io import BytesIO
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors

# ---------------------------
# Page config
# ---------------------------
st.set_page_config(page_title="Genset Price & Margin", layout="centered")

# ---------------------------
# Auth (simple password)
# ---------------------------
def _get_expected_password():
    # Prefer Streamlit secrets; fall back to environment variable.
    pw = st.secrets.get("APP_PASSWORD", None) if hasattr(st, "secrets") else None
    if not pw:
        pw = os.getenv("APP_PASSWORD", None)
    return pw

def _auth_gate():
    expected = _get_expected_password()
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if expected is None:
        st.info("🔒 No password configured. Set **APP_PASSWORD** in Streamlit Cloud secrets or environment variables.")
        # Allow access but show banner
        st.session_state.auth_ok = True
        return True

    if st.session_state.auth_ok:
        # Already signed in
        with st.sidebar:
            if st.button("Sign out"):
                st.session_state.auth_ok = False
                st.experimental_rerun()
        return True

    st.markdown("### 🔑 Enter Password")
    pwd = st.text_input("Password", type="password")
    if st.button("Sign in", type="primary"):
        if pwd == expected:
            st.session_state.auth_ok = True
            st.success("Signed in.")
            st.experimental_rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

_auth_gate()

# ---------------------------
# Branding header
# ---------------------------
logo_path = Path("assets/logo.png")
cols = st.columns([1,2,1])
with cols[1]:
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=False, width=180)
st.markdown("<h2 style='text-align:center;margin-top:0;'>💰 Genset Price & Margin Calculator</h2>", unsafe_allow_html=True)
st.caption("Upload the Excel with sheets **GENSETS**, **FUEL TANKS**, **BREAKERS**.")

# ---------------------------
# Helpers
# ---------------------------
def fmt_money(x):
    try:
        return f"${float(x):,.2f}"
    except:
        return "$0.00"

def build_pdf(payload: dict) -> BytesIO:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf)

    styles = getSampleStyleSheet()
    header = ParagraphStyle('Header', fontSize=12, textColor=colors.red, alignment=TA_CENTER, spaceAfter=12)
    title = ParagraphStyle('Title', fontSize=16, alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold')
    section = ParagraphStyle('Section', fontSize=13, spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold')
    normal = styles['Normal']; normal.fontSize = 11; normal.leading = 14

    def P(text, style=normal): return Paragraph(text, style)

    story = [
        P("Aksa Power Generation USA, Finance Department, Confidential", style=header),
        P("Profit Margin Summary", style=title),

        P("■ Genset Details", style=section),
        P(f"Genset Model: {payload['model']}"),
        P(f"Enclosure Type: {payload['enclosure']}"),
        P(f"Engine S/N: {payload['sn']}"),

        P("■ Cost Information", style=section),
        P(f"Genset Actual Cost: {fmt_money(payload['actual_cost'])}"),
        P(f"Genset Average Cost: {fmt_money(payload['avg_cost'])}"),
    ]

    if payload['tank_cost'] > 0:
        story.append(P(f"Fuel Tank Price: {fmt_money(payload['tank_cost'])}"))
    if payload['breaker_cost'] > 0:
        story.append(P(f"Breaker Cost: {fmt_money(payload['breaker_cost'])} "
                       f"(×{payload['breaker_qty']}, Unit: {fmt_money(payload['breaker_unit'])})"))

    story += [
        P(f"Total Actual Cost: {fmt_money(payload['total_actual'])}"),
        P("■ Selling Prices", style=section),
        P(f"Selling Price (Actual Cost + {payload['margin_pct']:.1f}%): {fmt_money(payload['price_actual'])}"),
        P(f"Selling Price (Avg Cost + {payload['margin_pct']:.1f}%): {fmt_money(payload['price_avg'])}"),
    ]
    if payload['sales_target'] and payload['sales_target'] > 0:
        story += [
            P("■ Sales Target", style=section),
            P(f"Sales Person Target Price: {fmt_money(payload['sales_target'])}"),
            P(f"Calculated Margin: {payload['calc_margin']:.2f}%")
        ]

    doc.build(story)
    buf.seek(0)
    return buf

# ---------------------------
# UI
# ---------------------------
uploaded = st.file_uploader("📂 Upload Excel (.xlsx)", type=["xlsx"])

if not uploaded:
    st.info("Upload the Excel file to begin.")
    st.stop()

# Read sheets
xls = pd.ExcelFile(uploaded)
gensets_df = pd.read_excel(xls, sheet_name="GENSETS")
tanks_df   = pd.read_excel(xls, sheet_name="FUEL TANKS")
breakers_df= pd.read_excel(xls, sheet_name="BREAKERS")

# Clean columns
for df in (gensets_df, tanks_df, breakers_df):
    df.columns = df.columns.str.strip()

# KW ranges
gensets_df["KW"] = pd.to_numeric(gensets_df["KW"], errors="coerce")
max_kw = float(gensets_df["KW"].max())
bins = [0, 100, 250, 400, 1000, max_kw + 1]
labels = ['1–100', '101–250', '251–400', '401–1000', '>1000']
gensets_df['KW RANGE'] = pd.cut(gensets_df['KW'], bins=bins, labels=labels, right=False)

st.divider()
c1, c2 = st.columns(2)

kw_range = c1.selectbox("KW Range", labels)
filtered_kw = gensets_df[gensets_df['KW RANGE'] == kw_range]

model_options = sorted(filtered_kw['MODEL'].dropna().unique().tolist())
model = c2.selectbox("Model", model_options)

filtered_model = gensets_df[(gensets_df['KW RANGE'] == kw_range) & (gensets_df['MODEL'] == model)]
encl_options = sorted(filtered_model['ENCLOSURE TYPE'].dropna().unique().tolist())
enclosure = st.selectbox("Canopy / Enclosure", encl_options)

filtered_encl = filtered_model[filtered_model['ENCLOSURE TYPE'] == enclosure]

def display_row(row):
    cost = float(row['Actual Item Cost'])
    return f"{row['ENGINE S/N']} | {fmt_money(cost)}"

genset_options = [display_row(r) for _, r in filtered_encl.iterrows()]
sn_display = st.selectbox("Select Genset (Engine S/N)", genset_options) if len(genset_options) > 0 else None

include_tank = st.checkbox("Include Fuel Tank?")
tank_model = None
if include_tank:
    tank_model = st.selectbox("Tank Option", sorted(tanks_df['Fuel Tank Model'].dropna().unique().tolist()))

include_breaker = st.checkbox("Include Breaker?")
breaker_model, breaker_qty = None, 1
if include_breaker:
    breaker_model = st.selectbox("Breaker Option", sorted(breakers_df['Breaker Model'].dropna().unique().tolist()))
    breaker_qty = st.number_input("Breaker Qty", min_value=1, value=1, step=1)

margin_pct = st.slider("Margin (%)", min_value=0.0, max_value=100.0, value=20.0, step=0.5)
sales_target = st.number_input("Sales Person Target Price ($)", min_value=0.0, value=0.0, step=100.0)

st.write("")  # spacing
show = st.button("💵 Show Summary", use_container_width=True)

if show and sn_display:
    sn = sn_display.split("|")[0].strip()
    row = gensets_df[gensets_df['ENGINE S/N'] == sn].iloc[0]
    actual_cost = float(row['Actual Item Cost'])

    avg_cost = float(gensets_df[
        (gensets_df['MODEL'] == model) &
        (gensets_df['ENCLOSURE TYPE'] == enclosure)
    ]['Actual Item Cost'].mean())

    tank_cost = 0.0
    if include_tank and tank_model:
        tr = tanks_df[tanks_df['Fuel Tank Model'] == tank_model]
        if not tr.empty:
            tank_cost = float(tr['Price'].values[0])

    breaker_cost, breaker_unit = 0.0, 0.0
    if include_breaker and breaker_model:
        br = breakers_df[breakers_df['Breaker Model'] == breaker_model]
        if not br.empty:
            breaker_unit = float(br['Price'].values[0])
            breaker_cost = breaker_unit * int(breaker_qty)

    total_actual = actual_cost + tank_cost + breaker_cost
    total_avg    = avg_cost + tank_cost + breaker_cost
    m = margin_pct/100.0
    price_actual = total_actual * (1+m)
    price_avg    = total_avg * (1+m)

    calc_margin = None
    if sales_target and sales_target > 0:
        calc_margin = ((sales_target - total_actual) / total_actual) * 100.0

    st.markdown("### 🔎 Selected Genset")
    st.dataframe(
        pd.DataFrame([{
            "ENGINE S/N": sn,
            "MODEL": model,
            "ENCLOSURE TYPE": enclosure,
            "Actual Item Cost": actual_cost
        }]),
        use_container_width=True
    )

    st.write("")  # spacing
    st.markdown("### 💰 Costs")
    st.write(f"• Genset Actual Cost: **{fmt_money(actual_cost)}**")
    st.write(f"• Genset Avg. Cost (Model + Canopy): **{fmt_money(avg_cost)}**")
    if tank_cost > 0:
        st.write(f"• Fuel Tank Price: **+{fmt_money(tank_cost)}**")
    if breaker_cost > 0:
        st.write(f"• Breaker: **{breaker_model} × {breaker_qty} = {fmt_money(breaker_cost)}**  (Unit: {fmt_money(breaker_unit)})")
    st.write(f"• Total Actual Cost: **{fmt_money(total_actual)}**")

    st.write("")  # spacing
    st.markdown("### 💵 Selling Prices")
    st.write(f"• From Actual Cost (+{margin_pct:.1f}%): **{fmt_money(price_actual)}**")
    st.write(f"• From Avg Cost   (+{margin_pct:.1f}%): **{fmt_money(price_avg)}**")

    if sales_target and sales_target > 0:
        st.write("")
        st.markdown("### 🎯 Sales Target")
        st.write(f"• Sales Person Target Price: **{fmt_money(sales_target)}**")
        st.write(f"• Profit Margin if Accepted: **{calc_margin:.2f}%**")

    # Extra spacing before download
    st.write("")
    st.write("")

    payload = dict(
        model=model, enclosure=enclosure, sn=sn,
        actual_cost=actual_cost, avg_cost=avg_cost,
        tank_cost=tank_cost, breaker_cost=breaker_cost,
        breaker_unit=breaker_unit, breaker_qty=int(breaker_qty),
        total_actual=total_actual, margin_pct=margin_pct,
        price_actual=price_actual, price_avg=price_avg,
        sales_target=sales_target, calc_margin=calc_margin if calc_margin is not None else 0.0
    )
    pdf_buf = build_pdf(payload)

    st.download_button(
        label="📄 Download PDF",
        data=pdf_buf,
        file_name="profit_margin_summary.pdf",
        mime="application/pdf",
        use_container_width=True
    )
