import streamlit as st
import pandas as pd

# --- Parsers ---
def parse_currency(raw, allow_blank=False):
    raw = raw.strip()
    if allow_blank and raw == "":
        return 0.0
    if raw.startswith("$"):
        raw = raw[1:]
    if raw.endswith("%"):
        raw = raw[:-1]
    return float(raw)

def parse_int(raw):
    raw = raw.strip()
    return int(raw) if raw else 0

def parse_sqft(raw):
    raw = raw.strip().replace(",", "")
    return float(raw)

# --- Calculation logic ---
def compute(opt):
    rate = parse_currency(opt['rate'])
    sf   = parse_sqft(opt['sqft'])
    term = parse_int(opt['term'])
    free = parse_int(opt['free'])
    ti   = parse_currency(opt['ti'], allow_blank=True)

    opex = 0.0
    if opt['service'] == 'NNN':
        opex = parse_currency(opt['opex'], allow_blank=True)

    # escalations
    btype, bamt = opt['base_esc_type'], parse_currency(opt['base_esc_amt'], allow_blank=True)
    otype, oamt = opt.get('opex_esc_type','None'), parse_currency(opt.get('opex_esc_amt',''), allow_blank=True)

    # commission
    ctype, camt = opt['comm_type'], parse_currency(opt['comm_amt'], allow_blank=True)

    years = term // 12
    rate_y, opex_y = rate, opex
    rows = []
    for y in range(1, years+1):
        if y>1:
            if btype=='Percentage': rate_y *= (1 + bamt/100)
            elif btype=='Dollar':    rate_y += bamt
            if opex>0:
                if otype=='Percentage': opex_y *= (1 + oamt/100)
                elif otype=='Dollar':    opex_y += oamt

        annual = (rate_y+opex_y)*sf
        monthly= annual/12
        row = {
            'Year':      y,
            'Rate/SF':   f"{rate_y:.2f}",
            'Monthly':   f"{monthly:,.2f}",
            'Annual':    f"{annual:,.2f}",
        }
        if opex>0:
            row['NNN/SF'] = f"{opex_y:.2f}"
        rows.append(row)

    df = pd.DataFrame(rows)

    total_rent    = sum(float(r['Annual'].replace(',','')) for r in rows)
    first_monthly = float(rows[0]['Monthly'].replace(',','')) if rows else 0
    free_disc     = first_monthly * free
    ti_disc       = ti * sf
    total_disc    = free_disc + ti_disc
    net_total     = total_rent - total_disc

    base_sum = sum(float(r['Rate/SF'])*sf for r in rows)
    if ctype=='Dollar':
        comm_value   = camt * sf * years
        comm_formula = f"{camt} * {sf} * {years} = {comm_value:,.0f}"
    elif ctype=='Percentage':
        comm_value   = (camt/100)*base_sum
        comm_formula = f"{camt}% * {base_sum:,.0f} = {comm_value:,.0f}"
    else:
        comm_value, comm_formula = 0.0, ""

    ner_year  = net_total/years
    ner_month = ner_year/12
    ner_psf   = ner_year/sf

    results = {
        'Total Rent Term':           (f"${total_rent:,.0f}", " + ".join(r['Annual'] for r in rows)+f" = {total_rent:,.0f}"),
        'Free Rent Discount':        (f"${free_disc:,.0f}", f"{first_monthly:,.0f} * {free} = {free_disc:,.0f}"),
        'TI Discount':               (f"${ti_disc:,.0f}", f"{ti:.2f} * {sf:,.0f} = {ti_disc:,.0f}"),
        'Total Discount':            (f"${total_disc:,.0f}", f"{free_disc:,.0f} + {ti_disc:,.0f} = {total_disc:,.0f}"),
        'Net Total After Discounts': (f"${net_total:,.0f}", f"{total_rent:,.0f} - {total_disc:,.0f} = {net_total:,.0f}"),
        'Leasing Commission':        (f"${comm_value:,.0f}", comm_formula),
        'NER per Year':              (f"${ner_year:,.2f}", f"{net_total:,.0f} / {years} = {ner_year:.2f}"),
        'NER per Month':             (f"${ner_month:,.2f}", f"{ner_year:.2f} / 12 = {ner_month:.2f}"),
        'NER per SF per Year':       (f"${ner_psf:,.2f}", f"{ner_year:.2f} / {sf:,.0f} = {ner_psf:.2f}"),
    }
    return df, results

# --- Streamlit App ---
st.set_page_config(layout="wide")

# default template for a blank option
DEFAULT = {
    'service':'Full Service','opex':'','opex_esc_type':'None','opex_esc_amt':'',
    'base_esc_type':'None','base_esc_amt':'',
    'rate':'','sqft':'','term':'','free':'','ti':'',
    'comm_type':'None','comm_amt':''
}

if 'options' not in st.session_state:
    st.session_state.options = [DEFAULT.copy()]
    st.session_state.active  = 0

def new_option(data=None):
    if len(st.session_state.options) < 5:
        entry = DEFAULT.copy() if data is None else data.copy()
        st.session_state.options.append(entry)
        st.session_state.active = len(st.session_state.options) - 1

def delete_option():
    if len(st.session_state.options) > 1:
        idx = st.session_state.active
        st.session_state.options.pop(idx)
        st.session_state.active = max(0, idx-1)

def duplicate_option():
    idx = st.session_state.active
    new_option(st.session_state.options[idx])

# Top buttons
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("New Option"):
        new_option()
with c2:
    if st.button("Duplicate Option"):
        duplicate_option()
with c3:
    if st.button("Delete Option"):
        delete_option()

# Tabs
tabs = st.tabs([f"Option {i+1}" for i in st.session_state.options])
for i, tab in enumerate(tabs):
    with tab:
        st.session_state.active = i
        opt = st.session_state.options[i]

        # inputs (unique keys)
        opt['service']        = st.selectbox("Service Type",
                                             ["Full Service","NNN"],
                                             index=["Full Service","NNN"].index(opt['service']),
                                             key=f"service_{i}")
        if opt['service']=="NNN":
            opt['opex']        = st.text_input("OPEX/SF (optional)", opt['opex'], key=f"opex_{i}")
            opt['opex_esc_type']= st.selectbox("OPEX Esc Type",
                                               ["None","Percentage","Dollar"],
                                               index=["None","Percentage","Dollar"].index(opt['opex_esc_type']),
                                               key=f"opex_esc_type_{i}")
            opt['opex_esc_amt']= st.text_input("OPEX Esc Amt", opt['opex_esc_amt'], key=f"opex_esc_amt_{i}")
        opt['base_esc_type']  = st.selectbox("Base Esc Type",
                                             ["None","Percentage","Dollar"],
                                             index=["None","Percentage","Dollar"].index(opt['base_esc_type']),
                                             key=f"base_esc_type_{i}")
        opt['base_esc_amt']   = st.text_input("Base Esc Amt", opt['base_esc_amt'], key=f"base_esc_amt_{i}")
        opt['rate']           = st.text_input("Base Rate/SF/year", opt['rate'], key=f"rate_{i}")
        opt['sqft']           = st.text_input("Square Feet", opt['sqft'], key=f"sqft_{i}")
        opt['term']           = st.text_input("Term in Months", opt['term'], key=f"term_{i}")
        opt['free']           = st.text_input("Free Rent Months", opt['free'], key=f"free_{i}")
        total_term_val        = parse_int(opt['term']) + parse_int(opt['free'])
        st.text_input("Total Term (auto)", str(total_term_val), disabled=True, key=f"total_{i}")
        opt['ti']             = st.text_input("TI Allowance/SF (opt)", opt['ti'], key=f"ti_{i}")
        opt['comm_type']      = st.selectbox("Commission Type (opt)",
                                              ["None","Percentage","Dollar"],
                                              index=["None","Percentage","Dollar"].index(opt['comm_type']),
                                              key=f"comm_type_{i}")
        opt['comm_amt']       = st.text_input("Commission Amt", opt['comm_amt'], key=f"comm_amt_{i}")

        if st.button("Calculate", key=f"calc_{i}"):
            try:
                df, results = compute(opt)
                st.dataframe(df, use_container_width=True)
                for label, (value, formula) in results.items():
                    st.markdown(f"**{label}** {value}")
                    if formula:
                        st.markdown(f"<span style='color:#666'>{formula}</span>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {e}")
