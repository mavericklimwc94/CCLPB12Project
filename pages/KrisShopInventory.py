# KrisShopInventory.py

import json
import random
import hashlib
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Sales Cart Inventory", layout="wide")

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

def norm(s):
    return " ".join((s or "").upper().split())

def gen_sku(brand, name):
    base = f"{brand.strip()}|{name.strip()}".upper()
    h = hashlib.sha1(base.encode("utf-8")).hexdigest()
    num = int(h[:8], 16) % 10_000_000
    return f"K{num:07d}"

def guess_price(brand, name):
    txt = f"{brand} {name}".lower()
    r = random.Random(norm(txt))
    
    if any(w in txt for w in ["whisky", "scotch", "cognac", "hennessy", "martell", "macallan", "glen", "champagne", "vodka", "gin"]):
        return int(round(r.uniform(60, 320)))
    if any(w in txt for w in ["edp", "edt", "cologne", "fragrance", "perfume"]):
        return int(round(r.uniform(80, 300)))
    if any(w in txt for w in ["cream", "serum", "mask", "essence", "treatment", "lotion", "skincare"]):
        return int(round(r.uniform(40, 260)))
    if any(w in txt for w in ["tea", "chocolate", "haribo", "toblerone", "lindt", "godiva"]):
        return int(round(r.uniform(10, 55)))
    if any(w in txt for w in ["sunglasses", "bag", "crossbody", "passport", "spinner", "bracelet", "lipstick", "makeup"]):
        return int(round(r.uniform(40, 350)))
    
    return int(round(r.uniform(30, 250)))

def load_catalog():
    if not CATALOG_JSON.exists():
        return []
    
    try:
        raw = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    except:
        return []
    
    items = []
    for it in raw:
        if not (it.get("brand") and it.get("name") and it.get("filename")):
            continue
        items.append({
            "brand": it.get("brand", "").strip(),
            "name": it.get("name", "").strip(),
            "filename": it.get("filename", "").strip(),
            "price": it.get("price"),
            "url": it.get("url", "").strip(),
        })
    
    result = []
    for it in items:
        b, n = it["brand"], it["name"]
        p = None
        
        for (ob, on), pv in PRICE_OVERRIDES.items():
            if norm(ob) == norm(b) and norm(on) == norm(n):
                p = int(round(pv))
                break
        
        if not p and norm(b) == "JOHNNIE WALKER" and "BLACK" in norm(n) and "1L" in norm(n):
            p = 49
        
        if not p and isinstance(it.get("price"), (int, float)):
            p = int(round(float(it["price"])))
        
        if not p:
            p = guess_price(b, n)

        result.append({
            "brand": b,
            "name": n,
            "filename": it["filename"],
            "url": it["url"],
            "price": int(p),
            "sku": gen_sku(b, n)
        })
    
    return result

def setup_bins(catalog):
    r = random.Random(42)
    idx_pool = list(range(len(catalog)))
    r.shuffle(idx_pool)
    bins = {}
    used = set()
    
    for bn in BINS:
        n = r.randint(3, 7)
        selected = []
        tries = 0
        
        while len(selected) < n and tries < 20000 and idx_pool:
            tries += 1
            i = idx_pool.pop()
            if i not in used:
                used.add(i)
                selected.append(i)
        
        bins[bn] = [catalog[i] for i in selected]
    
    return bins

def build_inventory(bins):
    inv = {}
    
    for cart in LS_CARTS:
        r = random.Random(hash(cart) & 0xffffffff)
        inv[cart] = {}
        
        for bn, items in bins.items():
            cart_items = []
            for it in items:
                q = r.randint(0, 2)
                cart_items.append({
                    "brand": it["brand"],
                    "name": it["name"],
                    "img": it["filename"],
                    "price": it["price"],
                    "sku": it["sku"],
                    "qty": q,
                    "dmg": 0,
                    "cart": q
                })
            inv[cart][bn] = cart_items
    
    return inv

def placeholder_img(w=48, h=48):
    st.markdown(
        f"<div style='width:{w}px;height:{h}px;border:1px solid #ccc;border-radius:8px;"
        "display:flex;align-items:center;justify-content:center;color:#777;font-size:10px;'>no img</div>",
        unsafe_allow_html=True
    )

st.markdown(
    '''
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
    ''',
    unsafe_allow_html=True
)

def parse_search(q):
    if not q or not q.strip():
        return None, None
    
    s = q.strip()
    
    if s[:1].upper() == 'K' or s.isdigit():
        pfx = s.upper().replace(' ', '')
        if not pfx.startswith('K'):
            pfx = 'K' + pfx
        return 'sku', pfx
    
    return 'name', s.lower()

def find_items(inv, mode, term):
    found = []
    
    for cart in LS_CARTS:
        for bn, items in inv[cart].items():
            cnt = 0
            
            if mode == 'sku':
                for it in items:
                    if str(it.get('sku', '')).upper().startswith(term):
                        cnt += int(it.get('qty', 0))
            else:
                for it in items:
                    b = it.get('brand', '').lower()
                    n = it.get('name', '').lower()
                    if term in b or term in n:
                        cnt += int(it.get('qty', 0))
            
            if cnt > 0:
                found.append((f"{cart} {bn}", cnt))
    
    return found

catalog = load_catalog()
st.title("Sales Cart Inventory")

if 'seen_notice' not in st.session_state:
    st.session_state.seen_notice = False

@st.dialog("Notice")
def notice():
    st.write("This Inventory List reflects the **initial inventory from ex-SIN**.\n\nSales crew should **verify availability in respective sales cart** before offering any item.")
    if st.button("I understand", type="primary", key="ok_btn"):
        st.session_state.seen_notice = True
        st.rerun()

if not st.session_state.seen_notice:
    notice()

if catalog:
    if 'bins' not in st.session_state:
        st.session_state.bins = setup_bins(catalog)
    if 'inv' not in st.session_state:
        st.session_state.inv = build_inventory(st.session_state.bins)

    inv = st.session_state.inv

    if 'search' not in st.session_state:
        st.session_state.search = ""
    
    l, r = st.columns([1, 1], vertical_alignment="bottom")
    with l:
        st.markdown("### Search Inventory")
    with r:
        q = st.text_input(
            label="search",
            value=st.session_state.search,
            key="search_box",
            label_visibility="collapsed",
            placeholder="Search by SKU or item name..."
        )
        st.session_state.search = q
    
    mode, term = parse_search(q)
    
    if term:
        _, rcol = st.columns([1, 1])
        with rcol:
            matches = find_items(inv, mode, term)
            if matches:
                txt = ", ".join([f"{loc}: {c} available" for loc, c in matches])
                st.success(txt)
            else:
                st.warning("No stock found for this search in any cart.")
    
    st.markdown("---")
    
    tabs = st.tabs(LS_CARTS)
    
    for i, cart in enumerate(LS_CARTS):
        with tabs[i]:
            st.subheader(cart)

            btabs = st.tabs(BINS)
            
            for j, bn in enumerate(BINS):
                with btabs[j]:
                    items = inv[cart][bn]

                    if term:
                        show = []
                        if mode == 'sku':
                            for it in items:
                                if str(it.get('sku','')).upper().startswith(term):
                                    show.append(it)
                        else:
                            for it in items:
                                b = it.get('brand','').lower()
                                n = it.get('name','').lower()
                                if term in b or term in n:
                                    show.append(it)
                        
                        if not show:
                            st.caption("No results in this bin for current search.")
                            continue
                        items = show

                    h1, h2, h3, h4, h5, h6 = st.columns([1, 6, 1, 1, 1, 2])
                    h1.markdown(" ", unsafe_allow_html=True)
                    h2.markdown("<span class='ks-header'>Item</span>", unsafe_allow_html=True)
                    h3.markdown("<span class='ks-header'>Qty</span>", unsafe_allow_html=True)
                    h4.markdown("<span class='ks-header'>Dmg</span>", unsafe_allow_html=True)
                    h5.markdown("<span class='ks-header'>Cart</span>", unsafe_allow_html=True)
                    h6.markdown("<span class='ks-header'>SKU</span>", unsafe_allow_html=True)

                    tot = 0
                    for it in items:
                        c1, c2, c3, c4, c5, c6 = st.columns([1, 6, 1, 1, 1, 2])
                        
                        img = IMAGE_DIR / it["img"]
                        if img.exists():
                            c1.image(str(img), width=48)
                        else:
                            with c1:
                                placeholder_img()
                        
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
                        tot += it["cart"]

                    st.markdown(
                        f"<div style='display:flex;justify-content:flex-end;margin-top:8px'>"
                        f"<span style='font-weight:700'>Total end: {tot}</span></div>",
                        unsafe_allow_html=True
                    )
else:
    st.warning("No catalog loaded. Please run your KrisShop downloader to create `catalog_krisshop.json`.")
