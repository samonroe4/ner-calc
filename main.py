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
def compute(schedule_input):
    rate = parse_currency(schedule_input['rate'])
    sf   = parse_sqft(schedule_input['sqft'])
    term = parse_int(schedule_input['term'])
    free = parse_int(schedule_input['free'])
    ti   = parse_currency(schedule_input['ti'], allow_blank=True)
    # OPEX
    opex = 0.0
    if schedule_input['service'] == 'NNN':
        opex = parse_currency(schedule_input['opex'], allow_blank=True)
    # Escalations
    btype = schedule_input['base_esc_type']
    bamt  = parse_currency(schedule_input['base_esc_amt'], allow_blank=True)
    otype = schedule_input.get('opex_esc_type','None')
    oamt  = parse_currency(schedule_input.get('opex_esc_amt',''), allow_blank=True)
    # Commission
    ctype = schedule_input['comm_type']
    camt  = parse_currency(schedule_input['comm_amt'], allow_blank=True)

    years = term // 12
    rate_y, opex_y = rate, opex
    schedule = []
    for y in range(1, years+1):
        if y>1:
            if btype=='Percentage':
                rate_y *= (1 + bamt/100)
            elif btype=='Dollar':
                rate_y += bamt
            if opex>0:
                if otype=='Percentage':
                    opex_y *= (1 + oamt/100)
                elif otype=='Dollar':
                    opex_y += oamt
        annual = (rate_y + opex_y)*sf
        monthly = annual/12
        schedule.append({'Year':y,
                         'Rate/SF':f"{rate_y:.2f}",
                         **({'NNN/SF':f"{opex_y:.2f}"} if opex>0 else {}),
                         'Monthly':f"{monthly:,.2f}",
                         'Annual':f"{annual:,.2f}"})
    df = pd.DataFrame(schedule)

    # Totals
    total_rent = sum(float(r['Annual'].replace(',','')) for r in schedule)
    first_monthly = float(schedule[0]['Monthly'].replace(',','')) if schedule else 0
    free_disc = first_monthly * free
    ti_disc   = ti * sf
    total_disc= free_disc + ti_disc
    net_total = total_rent - total_disc

    base_sum = sum(float(r['Rate/SF'])*sf for r in schedule)
    if ctype=='Dollar':
        comm_value = camt * sf * years
        comm_formula = f"{camt} * {sf} * {years} = {comm_value:,.0f}"
    elif ctype=='Percentage':
        comm_value = (camt/100)*base_sum
        comm_formula = f"{camt}% * {base_sum:,.0f} = {comm_value:,.0f}"
    else:
        comm_value, comm_formula = 0.0, ""

    ner_year = net_total/years
    ner_month= ner_year/12
    ner_psf  = ner_year/sf

    results = {
      'Total Rent Term':(f"${total_rent:,.0f}", " + ".join(r['Annual'] for r in schedule)+f" = {total_rent:,.0f}"),
      'Free Rent Discount':(f"${free_disc:,.0f}", f"{first_monthly:,.0f} * {free} = {free_disc:,.0f}"),
      'TI Discount':(f"${ti_disc:,.0f}", f"{ti:.2f} * {sf:,.0f} = {ti_disc:,.0f}"),
      'Total Discount':(f"${total_disc:,.0f}", f"{free_disc:,.0f} + {ti_disc:,.0f} = {total_disc:,.0f}"),
      'Net Total After Discounts':(f"${net_total:,.0f}", f"{total_rent:,.0f} - {total_disc:,.0f} = {net_total:,.0f}"),
      'Leasing Commission':(f"${comm_value:,.0f}", comm_formula),
      'NER per Year':(f"${ner_year:,.2f}", f"{net_total:,.0f} / {years} = {ner_year:.2f}"),
      'NER per Month':(f"${ner_month:,.2f}", f"{ner_year:.2f} / 12 = {ner_month:.2f}"),
      'NER per SF per Year':(f"${ner_psf:,.2f}", f"{ner_year:.2f} / {sf:,.0f} = {ner_psf:.2f}")
    }

    return df, results

# --- Streamlit App ---
st.set_page_config(layout="wide")
if 'options' not in st.session_state:
    # each option is a dict of inputs
    st.session_state.options = [{
      'service':'Full Service','opex':'','opex_esc_type':'None','opex_esc_amt':'',
      'base_esc_type':'None','base_esc_amt':'',
      'rate':'','sqft':'','term':'','free':'','ti':'',
      'comm_type':'None','comm_amt':''
    }]
    st.session_state.active = 0

def new_option(data=None):
    if len(st.session_state.options) < 5:
        base = {
          'service':'Full Service','opex':'','opex_esc_type':'None','opex_esc_amt':'',
          'base_esc_type':'None','base_esc_amt':'',
          'rate':'','sqft':'','term':'','free':'','ti':'',
          'comm_type':'None','comm_amt':''
        }
        st.session_state.options.append(data or base)
        st.session_state.active = len(st.session_state.options)-1

def delete_option():
    if len(st.session_state.options)>1:
        idx = st.session_state.active
        st.session_state.options.pop(idx)
        st.session_state.active = max(0, idx-1)

def duplicate_option():
    idx = st.session_state.active
    data = st.session_state.options[idx].copy()
    new_option(data)

# Top controls
c1, c2, c3 = st.columns([1,1,1])
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
tabs = st.tabs([f"Option {i+1}" for i in range(len(st.session_state.options))])
for i, tab in enumerate(tabs):
    with tab:
        st.session_state.active = i
        opt = st.session_state.options[i]
        # Inputs
        opt['service'] = st.selectbox("Service Type", ["Full Service","NNN"], index=["Full Service","NNN"].index(opt['service']))
        if opt['service']=="NNN":
            opt['opex'] = st.text_input("OPEX/SF (optional)", opt['opex'])
            opt['opex_esc_type'] = st.selectbox("OPEX Esc Type", ["None","Percentage","Dollar"], index=["None","Percentage","Dollar"].index(opt['opex_esc_type']))
            opt['opex_esc_amt']  = st.text_input("OPEX Esc Amt", opt['opex_esc_amt'])
        opt['base_esc_type'] = st.selectbox("Base Esc Type", ["None","Percentage","Dollar"], index=["None","Percentage","Dollar"].index(opt['base_esc_type']))
        opt['base_esc_amt']  = st.text_input("Base Esc Amt", opt['base_esc_amt'])
        opt['rate'] = st.text_input("Base Rate/SF/year", opt['rate'])
        opt['sqft'] = st.text_input("Square Feet", opt['sqft'])
        opt['term'] = st.text_input("Term in Months", opt['term'])
        opt['free'] = st.text_input("Free Rent Months", opt['free'])
        st.text_input("Total Term (auto)", str((parse_int(opt['term'])+parse_int(opt['free']))), disabled=True)
        opt['ti']   = st.text_input("TI Allowance/SF (opt)", opt['ti'])
        opt['comm_type'] = st.selectbox("Commission Type (opt)", ["None","Percentage","Dollar"], index=["None","Percentage","Dollar"].index(opt['comm_type']))
        opt['comm_amt']  = st.text_input("Commission Amt", opt['comm_amt'])

        # Compute and display
        if st.button("Calculate", key=f"calc_{i}"):
            try:
                df, results = compute(opt)
                st.dataframe(df, use_container_width=True)
                for k,(v,fmt) in results.items():
                    st.markdown(f"**{k}** {v}  ")
                    if fmt:
                        st.markdown(f"<span style='color:#666'>{fmt}</span>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error: {e}")

