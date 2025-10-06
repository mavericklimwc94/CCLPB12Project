import os, json, base64, mimetypes, random
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Combine eSGV", page_icon="💳", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
      [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("Combine eSGV")
st.caption("Select multiple SGVs to combine for the same passenger.")

def set_faded_bg():
    candidates = ["ui_bg.jpg"]
    img_path = next((p for p in candidates if os.path.exists(p)), None)
    if not img_path: 
        return
    mime, _ = mimetypes.guess_type(img_path)
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    st.markdown(f"""
    <style>
      [data-testid="stAppViewContainer"] {{
        background-image: linear-gradient(rgba(255,255,255,0.82), rgba(255,255,255,0.82)),
                          url("data:{mime};base64,{b64}");
        background-size: cover;
        background-position: center;
      }}
    </style>
    """, unsafe_allow_html=True)

set_faded_bg()

try:
    import qrcode
    QR_AVAILABLE = True
except Exception:
    QR_AVAILABLE = False

# Initialize session state
for key, default in [
    ("df", None), ("last_uploaded_name", None), ("picked_serials", set()),
    ("editor_nonce", 0), ("show_qr_dialog", False), ("qr_title", ""),
    ("qr_path", ""), ("undo_stack", [])
]:
    st.session_state.setdefault(key, default)

def load_initial_df(uploaded_file):
    if uploaded_file is not None: 
        return pd.read_csv(uploaded_file)
    for fn in ["big_sample_vouchers_v2.csv", "big_sample_vouchers.csv"]:
        if os.path.exists(fn): 
            return pd.read_csv(fn)
    return pd.DataFrame([
        ["51G","ABBOTT CLAIRE","SR1000000953",100,"Active","2026-01-01"],
        ["51G","ABBOTT CLAIRE","SR1000000954",75,"Active","2026-03-03"],
        ["51G","ABBOTT CLAIRE","SR1000000123",50,"Expired","2025-12-31"],
    ], columns=["Seat No.","Passenger","Voucher Serial No.","SGV Amount","Status","Date of Expiry"])

if st.session_state["df"] is None: 
    st.session_state["df"] = load_initial_df(None)

df = st.session_state["df"]
for col in ["Seat No.","Passenger","Voucher Serial No.","SGV Amount","Status","Date of Expiry"]:
    if col not in df.columns: 
        df[col] = ""
if "Remarks" in df.columns: 
    df.drop(columns=["Remarks"], inplace=True)

df["Passenger"] = df["Passenger"].astype(str)
df["Voucher Serial No."] = df["Voucher Serial No."].astype(str)
df["SGV Amount"] = pd.to_numeric(df["SGV Amount"], errors="coerce")

@st.dialog("⚙️ Settings")
def open_settings_dialog():
    st.subheader("Settings")
    uploaded = st.file_uploader("Upload vouchers CSV", type=["csv"], key="csv_uploader_modal")
    if uploaded is not None:
        st.session_state["df"] = load_initial_df(uploaded)
        st.session_state["last_uploaded_name"] = uploaded.name
        st.success(f"Loaded: {uploaded.name}")

def list_undo_records_for_passenger(pax):
    stack = st.session_state.get("undo_stack", [])
    results = []
    for i in range(len(stack)-1, -1, -1):
        rec = stack[i]
        if rec.get("type")=="combine" and rec.get("passenger")==pax:
            results.append((i, rec))
    return results

h1, h2, h3, h_set = st.columns([2, 2, 3, 0.6])
with h1:
    passenger = st.selectbox("Passenger", sorted(df["Passenger"].dropna().unique()))
with h2:
    only_active = st.checkbox("Only show Active vouchers", value=True)
    if list_undo_records_for_passenger(passenger):
        revert_inline_clicked = st.button("Revert Combined Voucher")
    else:
        revert_inline_clicked = False
with h3:
    selected_metric = st.empty()
with h_set:
    if st.button("⚙️", help="Settings", type="secondary"):
        open_settings_dialog()

toolbar_placeholder = st.container()

view = df[df["Passenger"] == passenger].copy()
if only_active:
    view = view[view["Status"].astype(str).str.lower() == "active"]
view = view.reset_index(drop=True)

table = view.copy()
table.insert(0, "Select", False)

with toolbar_placeholder:
    tb_spacer, tb_combine_col, tb_clear_col = st.columns([6.2, 1.4, 1.4])
    combine_slot = tb_combine_col.empty()
    clear_slot = tb_clear_col.empty()

edited = st.data_editor(
    table, use_container_width=True, hide_index=True,
    column_config={
        "Select": st.column_config.CheckboxColumn(""),
        "SGV Amount": st.column_config.NumberColumn(format="%d"),
        "Date of Expiry": st.column_config.DateColumn(format="YYYY-MM-DD"),
    },
    disabled=[c for c in table.columns if c != "Select"],
    key=f"editor_{passenger}_{only_active}_{st.session_state['editor_nonce']}",
)

current_checked = set(edited.loc[edited["Select"], "Voucher Serial No."].astype(str).tolist())
visible_serials = set(view["Voucher Serial No."].astype(str).tolist())
st.session_state["picked_serials"] -= (st.session_state["picked_serials"] & visible_serials) - current_checked
st.session_state["picked_serials"] |= current_checked

picked_list = sorted(list(st.session_state["picked_serials"]))
picked_rows_all = df[df["Voucher Serial No."].isin(picked_list)].copy()
cross_passenger = len(picked_rows_all["Passenger"].unique()) > 1 if not picked_rows_all.empty else False
picked_rows_current_pax = df[df["Voucher Serial No."].isin(picked_list) & (df["Passenger"] == passenger)].copy()

selected_metric.metric("Selected", len(picked_rows_current_pax))

total_value = float(picked_rows_current_pax["SGV Amount"].fillna(0).sum()) if not picked_rows_current_pax.empty else 0.0
can_combine = (len(picked_rows_current_pax) >= 2) and (not cross_passenger)

combine_clicked = combine_slot.button("Combine selected", type="primary", disabled=not can_combine)
clear_clicked = clear_slot.button("Clear selection", type="secondary")

if clear_clicked:
    st.session_state["picked_serials"] = set()
    st.session_state["editor_nonce"] += 1
    st.rerun()

if cross_passenger:
    st.warning("eSGVs cannot be combined with multiple passengers. Please clear selection.")

def new_serial(prefix="SR"):
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}{ts}{random.randint(1000,9999)}"

def generate_qr_and_update(picked_serials, passenger_name):
    base_df = st.session_state["df"]
    picked_rows = base_df[base_df["Voucher Serial No."].isin(picked_serials) & 
                          (base_df["Passenger"] == passenger_name)].copy()
    if len(picked_rows) < 2: 
        return
    
    source_serials = [str(s) for s in picked_rows["Voucher Serial No."].tolist()]
    total = float(picked_rows["SGV Amount"].fillna(0).sum())
    new_sn = new_serial()
    
    payload = {
        "combined_serial": new_sn, 
        "passenger": passenger_name, 
        "total_amount": total, 
        "source_serials": source_serials, 
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    out_dir = "out"
    os.makedirs(out_dir, exist_ok=True)
    img_path = os.path.join(out_dir, f"SGV_{new_sn}.png")
    
    if QR_AVAILABLE:
        qrcode.make(json.dumps(payload, separators=(",",":"))).save(img_path)
    else:
        with open(img_path.replace(".png",".json"), "w") as f: 
            json.dump(payload, f, indent=2)
    
    mask = base_df["Voucher Serial No."].isin(source_serials) & (base_df["Passenger"] == passenger_name)
    base_df.loc[mask, "Status"] = "Redeemed"
    
    new_row = {
        "Seat No.":"", 
        "Passenger": passenger_name, 
        "Voucher Serial No.": new_sn, 
        "SGV Amount": total, 
        "Status":"Redeemed", 
        "Date of Expiry": ""
    }
    st.session_state["df"] = pd.concat([base_df, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state["undo_stack"].append({
        "type":"combine", 
        "passenger": passenger_name, 
        "new_serial": new_sn, 
        "sources": source_serials, 
        "total_amount": total, 
        "qr_path": img_path, 
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })
    
    st.session_state["picked_serials"] = set()
    st.session_state["editor_nonce"] += 1
    st.session_state["qr_title"] = f"QR for {new_sn} – {passenger_name} (Total {total:.2f})"
    st.session_state["qr_path"] = img_path
    st.session_state["show_qr_dialog"] = True
    st.rerun()

@st.dialog("Confirm Combination")
def show_confirm_dialog():
    msg = f"I confirm combining {len(picked_rows_current_pax)} vouchers with a total value of ${total_value:,.2f} for Passenger {passenger}."
    st.warning(msg)
    agree = st.checkbox("Yes, proceed", value=False)
    if st.button("Generate QR", type="primary", disabled=not agree) and agree:
        generate_qr_and_update(picked_rows_current_pax["Voucher Serial No."].astype(str).tolist(), passenger)

if combine_clicked and can_combine:
    show_confirm_dialog()

def revert_combine_at_index(idx):
    stack = st.session_state.get("undo_stack", [])
    if not (0 <= idx < len(stack)): 
        return
    rec = stack.pop(idx)
    base_df = st.session_state["df"]
    
    src = rec.get("sources", [])
    if src: 
        base_df.loc[base_df["Voucher Serial No."].isin(src), "Status"] = "Active"
    base_df = base_df[base_df["Voucher Serial No."] != rec.get("new_serial")]
    st.session_state["df"] = base_df.reset_index(drop=True)
    
    try:
        if rec.get("qr_path") and os.path.exists(rec["qr_path"]): 
            os.remove(rec["qr_path"])
    except Exception: 
        pass
    
    st.session_state["show_qr_dialog"] = False
    st.session_state["qr_title"] = ""
    st.session_state["qr_path"] = ""
    st.session_state["picked_serials"] = set()
    st.session_state["editor_nonce"] += 1
    st.rerun()

@st.dialog("Confirm Revert")
def show_revert_confirm_dialog(pax):
    options = list_undo_records_for_passenger(pax)
    if not options: 
        return
    idx, rec = options[0]
    new_sn = rec.get("new_serial", "")
    count = len(rec.get("sources", []))
    total = rec.get("total_amount", 0.0)
    
    st.warning(f"I confirm reverting the last combination for Passenger {pax}: remove {new_sn} (total ${total:,.2f}) and restore {count} vouchers to Active.")
    agree = st.checkbox("Yes, revert", value=False)
    if st.button("Revert now", type="primary", disabled=not agree) and agree:
        revert_combine_at_index(idx)

@st.dialog("Revert a Combined Voucher")
def show_revert_pick_dialog(pax):
    options = list_undo_records_for_passenger(pax)
    if not options: 
        return
    
    labels = []
    indices = []
    for idx, rec in options:
        serial = rec.get("new_serial", "")
        ts = rec.get("timestamp", "")
        nsrc = len(rec.get("sources", []))
        total = rec.get("total_amount", 0.0)
        labels.append(f"{serial} – ${total:,.2f} – {nsrc} source(s) – {ts}")
        indices.append(idx)
    
    choice = st.selectbox("Pick a combined voucher to revert", 
                         options=list(range(len(indices))), 
                         format_func=lambda i: labels[i])
    st.info("Confirm to revert the selected combined voucher.")
    agree = st.checkbox("Yes, revert the selected voucher", value=False)
    if st.button("Revert now", type="primary", disabled=not agree) and agree:
        revert_combine_at_index(indices[choice])

if revert_inline_clicked:
    opts = list_undo_records_for_passenger(passenger)
    if len(opts) > 1:
        show_revert_pick_dialog(passenger)
    else:
        show_revert_confirm_dialog(passenger)

@st.dialog("QR Code")
def show_qr_dialog(title, img_path):
    st.image(img_path, caption=title, width=320)
    if st.button("Close"):
        st.session_state["show_qr_dialog"] = False
        st.rerun()

if st.session_state.get("show_qr_dialog") and st.session_state.get("qr_path"):
    show_qr_dialog(st.session_state["qr_title"], st.session_state["qr_path"])

# Navigation to KrisShop Inventory
with st.popover("Navigate"):
    st.write("App preferences")
    if st.button("Go to KrisShop Inventory"):
        try:
            st.switch_page("pages/KrisShopInventory.py")
        except Exception:
            st.error("Could not navigate. Expected path: pages/KrisShopInventory.py")
