import json
import random
import hashlib
from pathlib import Path
import streamlit as st

IMAGE_DIR = Path("images")
CATALOG_JSON = Path("catalog_krisshop.json")
BINS = ["Bin 1", "Bin 2", "Bin A", "Bin B", "Bin C", "Bin D", "Bin E", "Bin F", "Bin G"]
LS_CARTS = ["S1", "S2", "S3"]

PRICE_OVERRIDES = {
    ("COACH", "Women Miniatures Set"): 71,
    ("MARC JACOBS", "Miniature Fragrance Set"): 61,
    ("DIPTYQUE", "Orpheon EDP 75ml"): 268,
    ("DIPTYQUE", "Eau Rose EDT 100ml"): 209,
    ("TWG TEA", "1837 Black Tea 100g"): 45,
    ("JOHNNIE WALKER", "Black Label 12YO 1L"): 49,
    ("JOHNNIE WALKER", "Black Label 12 Year Old 1L"): 49,
    ("JOHNNIE WALKER", "Black Label Aged 12 Years Blended Scotch Whisky - 1L"): 49,
    ("TOM FORD", "Ombre Leather EDP 100ml"): 270,
    ("SK-II", "Facial Treatment Essence 230ml"): 325,
    ("KIEHL'S", "Ultra Facial Cream 50ml"): 60,
    ("SHISEIDO", "Ultimune Power Infusing Concentrate 50ml"): 150,
    ("GLENFIDDICH", "12 Year Old 1L"): 89,
    ("MACALLAN", "Double Cask 12YO 0.7L"): 129,
}

def _norm(s: str) -> str:
    return " ".join((s or "").upper().split())

def generate_sku(brand: str, name: str) -> str:
    base = f"{brand.strip()}|{name.strip()}".upper()
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()
    num = int(digest[:8], 16) % 10_000_000
    return f"K{num:07d}"

def heuristic_price(brand: str, name: str) -> int:
    text = f"{brand} {name}".lower()
    rnd = random.Random(_norm(text))
    if any(k in text for k in ["whisky", "scotch", "cognac", "hennessy", "martell", "macallan", "glen", "champagne", "vodka", "gin"]):
        return int(round(rnd.uniform(60, 320)))
    if any(k in text for k in ["edp", "edt", "cologne", "fragrance", "perfume"]):
        return int(round(rnd.uniform(80, 300)))
    if any(k in text for k in ["cream", "serum", "mask", "essence", "treatment", "lotion", "skincare"]):
        return int(round(rnd.uniform(40, 260)))
    if any(k in text for k in ["tea", "chocolate", "haribo", "toblerone", "lindt", "godiva"]):
        return int(round(rnd.uniform(10, 55)))
    if any(k in text for k in ["sunglasses", "bag", "crossbody", "passport", "spinner", "bracelet", "lipstick", "makeup"]):
        return int(round(rnd.uniform(40, 350)))
    return int(round(rnd.uniform(30, 250)))

def load_and_price_catalog():
    data = []
    if CATALOG_JSON.exists():
        try:
            raw = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
            data = [
                {
                    "brand": it.get("brand", "").strip(),
                    "name": it.get("name", "").strip(),
                    "filename": it.get("filename", "").strip(),
                    "price": it.get("price"),
                    "url": it.get("url", "").strip(),
                }
                for it in raw
                if it.get("brand") and it.get("name") and it.get("filename")
            ]
        except Exception:
            data = []
    
    priced = []
    for it in data:
        b, n = it["brand"], it["name"]
        price = None
        
        for (ob, on), pv in PRICE_OVERRIDES.items():
            if _norm(ob) == _norm(b) and _norm(on) == _norm(n):
                price = int(round(pv))
                break
        
        if price is None and _norm(b) == "JOHNNIE WALKER" and "BLACK" in _norm(n) and "1L" in _norm(n):
            price = 49
        
        if price is None and isinstance(it.get("price"), (int, float)):
            price = int(round(float(it["price"])))
        if price is None:
            price = heuristic_price(b, n)

        priced.append({
            **it,
            "price": int(price),
            "sku": generate_sku(b, n),
        })
    return priced

def build_bin_templates(catalog, min_items=3, max_items=7):
    rng = random.Random(42)
    pool = list(range(len(catalog)))
    rng.shuffle(pool)
    templates = {}
    used = set()
    
    for b in BINS:
        n = rng.randint(min_items, max_items)
        bin_idxs = []
        attempts = 0
        while len(bin_idxs) < n and attempts < 20000 and pool:
            attempts += 1
            idx = pool.pop()
            if idx in used:
                continue
            used.add(idx)
            bin_idxs.append(idx)
        templates[b] = [catalog[i] for i in bin_idxs]
    return templates

def make_inventory_from_templates(templates):
    inv = {}
    for code in LS_CARTS:
        rng = random.Random(hash(code) & 0xffffffff)
        inv[code] = {}
        for b, items in templates.items():
            cloned = []
            for it in items:
                qty_val = rng.randint(0, 2)
                cloned.append({
                    "brand": it["brand"],
                    "name": it["name"],
                    "img": it["filename"],
                    "price": it["price"],
                    "sku": it["sku"],
                    "qty": qty_val,
                    "dmg": 0,
                    "cart": qty_val
                })
            inv[code][b] = cloned
    return inv

def placeholder(width=48, height=48):
    st.markdown(
        f"<div style='width:{width}px;height:{height}px;border:1px solid #ccc;border-radius:8px;"
        "display:flex;align-items:center;justify-content:center;color:#777;font-size:10px;'>no img</div>",
        unsafe_allow_html=True
    )

st.markdown('''
    <style>
    .ks-header { font-weight:700; font-size:16px; }
    .ks-cell   { font-size:18px; }
    .ks-title  { font-size:15px; }
    .ks-sub    { color:#555; font-size:13px; }
    .ks-price  { color:#333; font-size:14px; margin-top:4px; }
    .stTabs [role="tab"] { padding: 12px 18px !important; }
    .stTabs [role="tab"] p { font-size: 17px !important; font-weight: 600 !important; }
    h2 { font-size: 1.6rem !important; }
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none !important; }
    .main .block-container { padding-left: 2rem !important; padding-right: 2rem !important; }
    </style>
    ''', unsafe_allow_html=True)

def normalize_query_to_prefix(q_raw: str):
    if not q_raw:
        return None
    q = q_raw.strip().upper().replace(" ", "")
    if not q:
        return None
    if q.startswith("K"):
        return q
    return "K" + q

def locate_across_carts_with_counts(inv: dict, prefix: str):
    entries = []
    for code in LS_CARTS:
        for bname, items in inv[code].items():
            count = sum(int(it.get("qty", 0)) for it in items if str(it.get("sku", "")).upper().startswith(prefix))
            if count > 0:
                entries.append((f"{code} {bname}", count))
    return entries

catalog = load_and_price_catalog()
st.title("Initial Inventory List")

if catalog:
    if "bin_templates" not in st.session_state:
        st.session_state.bin_templates = build_bin_templates(catalog, 3, 7)
    if "inventory_ls" not in st.session_state:
        st.session_state.inventory_ls = make_inventory_from_templates(st.session_state.bin_templates)

    inv = st.session_state.inventory_ls

    ls_tabs = st.tabs(LS_CARTS)
    for ls_idx, ls_code in enumerate(LS_CARTS):
        with ls_tabs[ls_idx]:
            left, right = st.columns([3, 2], vertical_alignment="center")
            with left:
                st.subheader(ls_code)
            with right:
                st.markdown("<div style='text-align:right; font-weight:600;'>Search by SKU</div>", unsafe_allow_html=True)
                raw_query = st.text_input(
                    label="sku_search_"+ls_code,
                    value="",
                    key="sku_search_"+ls_code,
                    label_visibility="collapsed",
                )
                prefix = normalize_query_to_prefix(raw_query)

                if prefix:
                    entries = locate_across_carts_with_counts(inv, prefix)
                    if entries:
                        msg = ", ".join([f"{label}: {cnt} available" for label, cnt in entries])
                        st.success(msg)
                    else:
                        st.warning("No stock found for this SKU prefix in any cart.")

            bin_tabs = st.tabs(BINS)
            for b_idx, bname in enumerate(BINS):
                with bin_tabs[b_idx]:
                    items = inv[ls_code][bname]

                    if prefix:
                        items_to_show = [it for it in items if str(it.get("sku", "")).upper().startswith(prefix)]
                        if not items_to_show:
                            st.caption("No results in this bin for current search.")
                            continue
                    else:
                        items_to_show = items

                    h1, h2, h3, h4, h5, h6 = st.columns([1, 6, 1, 1, 1, 2])
                    h1.markdown(" ", unsafe_allow_html=True)
                    h2.markdown("<span class='ks-header'>Item</span>", unsafe_allow_html=True)
                    h3.markdown("<span class='ks-header'>Qty</span>", unsafe_allow_html=True)
                    h4.markdown("<span class='ks-header'>Dmg</span>", unsafe_allow_html=True)
                    h5.markdown("<span class='ks-header'>Cart</span>", unsafe_allow_html=True)
                    h6.markdown("<span class='ks-header'>SKU</span>", unsafe_allow_html=True)

                    total = 0
                    for it in items_to_show:
                        c1, c2, c3, c4, c5, c6 = st.columns([1, 6, 1, 1, 1, 2])

                        img_path = IMAGE_DIR / it["img"]
                        if img_path.exists():
                            c1.image(str(img_path), width=48)
                        else:
                            with c1:
                                placeholder()

                        c2.markdown(
                            f"<div class='ks-title'><strong>{it['brand']}</strong></div>"
                            f"<div class='ks-sub'>{it['name']}</div>"
                            f"<div class='ks-price'>SGD {int(it['price']):,}</div>",
                            unsafe_allow_html=True
                        )
                        c3.markdown(f"<div class='ks-cell'>{it['qty']}</div>", unsafe_allow_html=True)
                        c4.markdown(f"<div class='ks-cell'>{it['dmg']}</div>", unsafe_allow_html=True)
                        c5.markdown(f"<div class='ks-cell'>{it['cart']}</div>", unsafe_allow_html=True)
                        c6.code(it["sku"])
                        total += it["cart"]

                    st.markdown(
                        f"<div style='display:flex;justify-content:flex-end;margin-top:8px'>"
                        f"<span style='font-weight:700'>Total end: {total}</span></div>",
                        unsafe_allow_html=True
                    )
else:
    st.warning("No catalog loaded. Please run your KrisShop downloader to create `catalog_krisshop.json`.")

# Navigation back to eSGV
with st.popover("Navigate"):
    st.write("App preferences")
    if st.button("Go back to Combine eSGV"):
        try:
            st.switch_page("eSGV.py")
        except Exception:
            st.error("Could not navigate. Expected path: eSGV.py")
