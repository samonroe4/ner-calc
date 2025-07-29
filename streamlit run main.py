import streamlit as st
import pandas as pd

# --- Parsers ---
def parse_currency(raw, allow_blank=False):
    raw = str(raw).strip()
    if allow_blank and raw == "":
        return 0.0
    if raw.startswith("$"):
        raw = raw[1:]
    if raw.endswith("%"):
        raw = raw[:-1]
    try:
        return float(raw)
    except ValueError:
        st.error("Enter a number like 25.50, $25.50, 3%, or 3")
        st.stop()

def parse_int(raw):
    raw = str(raw).strip()
    try:
        return int(raw) if raw else 0
    except ValueError:
        st.error("Enter an integer value")
        st.stop()

def parse_sqft(raw):
    raw = str(raw).strip().replace(",", "")
    try:
        return float(raw)
    except ValueError:
        st.error("Enter square feet like 2500 or 2,500")
        st.stop()

# --- Streamlit App ---
st.set_page_config(page_title="NER & Commission Calculator", layout="centered")
st.title("Net Effective Rent & Commission Calculator")

service_type = st.selectbox("Service Type", ["Full Service", "NNN"])

if service_type == "NNN":
    opex = st.text_input("OPEX/SF (optional)", "")
    opex_esc_type = st.selectbox("OPEX Escalation Type", ["None", "Percentage", "Dollar"])
    opex_esc_amt = st.text_input("OPEX Escalation Amt", "")
else:
    opex, opex_esc_type, opex_esc_amt = "0", "None", "0"

base_esc_type = st.selectbox("Base Escalation Type", ["None", "Percentage", "Dollar"])
base_esc_amt = st.text_input("Base Escalation Amt", "")

rate = st.text_input("Base Rate/SF/year", "")
sf = st.text_input("Square Feet", "")
term = st.text_input("Term in Months", "")
free_months = st.text_input("Free Rent Months", "")
ti_allowance = st.text_input("TI Allowance/SF (opt)", "")

comm_type = st.selectbox("Commission Type (opt)", ["None", "Percentage", "Dollar"])
comm_amt = st.text_input("Commission Amt", "")

if st.button("Calculate"):
    # parse inputs
    r = parse_currency(rate)
    sf_val = parse_sqft(sf)
    term_val = parse_int(term)
    free_val = parse_int(free_months)
    ti = parse_currency(ti_allowance, allow_blank=True)
    opex_val = parse_currency(opex, allow_blank=True)
    b_amt = parse_currency(base_esc_amt, allow_blank=True)
    o_amt = parse_currency(opex_esc_amt, allow_blank=True)
    c_amt = parse_currency(comm_amt, allow_blank=True)

    years = term_val // 12 or 1
    rate_y = r
    opex_y = opex_val
    schedule = []

    for y in range(1, years + 1):
        if y > 1:
            if base_esc_type == "Percentage":
                rate_y *= (1 + b_amt / 100)
            elif base_esc_type == "Dollar":
                rate_y += b_amt
            if service_type == "NNN":
                if opex_esc_type == "Percentage":
                    opex_y *= (1 + o_amt / 100)
                elif opex_esc_type == "Dollar":
                    opex_y += o_amt

        total_rate = rate_y + (opex_y if service_type == "NNN" else 0)
        annual = total_rate * sf_val
        monthly = annual / 12

        row = {
            "Year": y,
            "Rate/SF": round(rate_y, 2),
            **({"NNN/SF": round(opex_y, 2)} if service_type == "NNN" else {}),
            "Monthly": round(monthly, 2),
            "Annual": round(annual, 2),
        }
        schedule.append(row)

    df = pd.DataFrame(schedule)
    st.subheader("Annual Schedule")
    st.dataframe(df)

    total_rent = df["Annual"].sum()
    free_disc = df.iloc[0]["Monthly"] * free_val if not df.empty else 0
    ti_disc = ti * sf_val
    total_disc = free_disc + ti_disc
    net_total = total_rent - total_disc

    if comm_type == "Dollar":
        commission = c_amt * sf_val * years
    elif comm_type == "Percentage":
        base_sum = r * sf_val * years
        commission = (c_amt / 100) * base_sum
    else:
        commission = 0

    ner_year = net_total / years
    ner_month = ner_year / 12
    ner_psf_year = ner_year / sf_val if sf_val else 0

    st.subheader("Results")
    st.markdown(f"**Total Rent Term:** ${total_rent:,.0f}")
    st.markdown(f"**Free Rent Discount:** ${free_disc:,.0f}")
    st.markdown(f"**TI Discount:** ${ti_disc:,.0f}")
    st.markdown(f"**Total Discount:** ${total_disc:,.0f}")
    st.markdown(f"**Net Total After Discounts:** ${net_total:,.0f}")
    st.markdown(f"**Leasing Commission:** ${commission:,.0f}")
    st.markdown(f"**NER per Year:** ${ner_year:,.2f}")
    st.markdown(f"**NER per Month:** ${ner_month:,.2f}")
    st.markdown(f"**NER per SF per Year:** ${ner_psf_year:,.2f}")
