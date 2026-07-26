import os
import math
import requests
import streamlit as st
import folium
from folium import Map, Marker, Circle, PolyLine, Element
from streamlit_folium import st_folium
import flexpolyline as fp
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# ---- Google Sheets (gspread) ----
_gspread_ready = False
try:
    import gspread
    from google.oauth2.service_account import Credentials
    _gspread_ready = True
except Exception:
    _gspread_ready = False

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# =========================================================
# ORIGEN FIJO DEL ALMACÉN (no editable desde la interfaz)
# =========================================================
ORIGIN_ADDRESS = "Almacén (origen fijo)"
ORIGIN_LAT = 40.42995450669478
ORIGIN_LON = -3.644614746858031

# =========================================================
# TARIFAS POR DEFECTO
# (se sobreescriben con los valores de la hoja de control si existe)
# =========================================================
ZONA_1_KM = 3
ZONA_2_KM = 5
ZONA_3_KM = 10
ZONA_4_KM = 20

PRECIO_ZONA_1 = 25
PRECIO_ZONA_2 = 35
PRECIO_ZONA_3 = 50
PRECIO_ZONA_4 = 70
PRECIO_POR_KM_EXTRA = 1

# Dimensiones reales del camión, en las unidades "humanas" (metros/kg) que
# se usan en el resto de la app. A partir de aquí se convierten a lo que
# pide HERE Routing v8: height/width/length en CENTÍMETROS ENTEROS.
TRUCK_HEIGHT_M = 4
TRUCK_WIDTH_M = 2.5
TRUCK_LENGTH_M = 10
TRUCK_GROSS_WEIGHT_KG = 16000
TRUCK_AXLE_COUNT = 2

# HERE Routing v8 exige notación de corchetes para los atributos de camión,
# "straight" es el tipo de vehículo válido (no "delivery"), y height/width/
# length deben mandarse como enteros en centímetros (no metros con decimales;
# por eso "truck[width]": 2.5 daba "Invalid value for parameter 'truck[width]'").
TRUCK_PARAMS = {
    "truck[height]": int(round(TRUCK_HEIGHT_M * 100)),
    "truck[width]": int(round(TRUCK_WIDTH_M * 100)),
    "truck[length]": int(round(TRUCK_LENGTH_M * 100)),
    "truck[grossWeight]": TRUCK_GROSS_WEIGHT_KG,
    "truck[axleCount]": TRUCK_AXLE_COUNT,
    "truck[type]": "straight",
}

FIELDNAMES = [
    "timestamp_iso",
    "cliente_nombre", "operario_codigo",
    "origin_address", "origin_lat", "origin_lon",
    "dest_input_address", "dest_input_postal", "dest_input_city",
    "dest_geocoded_title", "dest_lat", "dest_lon",
    "distance_km", "duration_seconds", "duration_human", "price_eur",
    "zona_1_km", "zona_2_km", "zona_3_km", "zona_4_km",
    "precio_z1", "precio_z2", "precio_z3", "precio_z4", "precio_km_extra",
    "truck_height", "truck_width", "truck_length", "truck_gross_weight",
    "truck_axle_count", "truck_type",
]

# =========================================================
# CONFIGURACIÓN REMOTA (hoja de control "portes_config")
# =========================================================
def sheets_client_from_secrets():
    """Crea un cliente de gspread usando las credenciales de Streamlit Secrets."""
    if not _gspread_ready:
        raise RuntimeError("gspread/google-auth no están instalados.")
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Falta 'gcp_service_account' en st.secrets.")
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SHEETS_SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def load_remote_config(control_sheet_id: str) -> dict:
    """Lee pares clave/valor de la pestaña 'config' en la hoja de control."""
    gc = sheets_client_from_secrets()
    sh = gc.open_by_key(control_sheet_id)
    try:
        ws = sh.worksheet("config")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.get_worksheet(0)
    rows = ws.get_all_values()
    cfg = {}
    for r in rows:
        if len(r) >= 2 and r[0] and r[1]:
            cfg[r[0].strip()] = r[1].strip()
    return cfg

def cfg_int(cfg, key, default):
    try:
        return int(float(cfg[key]))
    except Exception:
        return default

def cfg_float(cfg, key, default):
    try:
        return float(cfg[key])
    except Exception:
        return default

REMOTE_CONTROL_ID = st.secrets.get("CONTROL_SHEET_ID", "")
REMOTE_CFG = {}
if REMOTE_CONTROL_ID:
    try:
        REMOTE_CFG = load_remote_config(REMOTE_CONTROL_ID)
    except Exception as e:
        st.sidebar.warning(f"No se pudo leer la hoja de control: {e}")

# La hoja de control (si existe) se usa como fuente de los valores por defecto.
ZONA_1_KM = cfg_int(REMOTE_CFG, "ZONA_1_KM", ZONA_1_KM)
ZONA_2_KM = cfg_int(REMOTE_CFG, "ZONA_2_KM", ZONA_2_KM)
ZONA_3_KM = cfg_int(REMOTE_CFG, "ZONA_3_KM", ZONA_3_KM)
ZONA_4_KM = cfg_int(REMOTE_CFG, "ZONA_4_KM", ZONA_4_KM)
PRECIO_ZONA_1 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_1", PRECIO_ZONA_1)
PRECIO_ZONA_2 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_2", PRECIO_ZONA_2)
PRECIO_ZONA_3 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_3", PRECIO_ZONA_3)
PRECIO_ZONA_4 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_4", PRECIO_ZONA_4)
PRECIO_POR_KM_EXTRA = cfg_float(REMOTE_CFG, "PRECIO_POR_KM_EXTRA", PRECIO_POR_KM_EXTRA)

def get_api_key():
    if "HERE_API_KEY" in st.secrets:
        return st.secrets["HERE_API_KEY"]
    env_key = os.getenv("HERE_API_KEY")
    if env_key:
        return env_key
    return None

# =========================================================
# HERE Geocoding / Routing
# =========================================================
def geocode_address(address, apikey, postal_code=None, city=None):
    base = "https://geocode.search.hereapi.com/v1/geocode"
    q = address
    if postal_code:
        q += f", {postal_code}"
    if city:
        q += f", {city}"
    params = {"q": q, "apikey": apikey, "limit": 1}
    r = requests.get(base, params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Geocoding failed: {r.status_code} - {r.text}")
    data = r.json()
    if not data.get("items"):
        raise ValueError("No results for that address.")
    item = data["items"][0]
    lat = item["position"]["lat"]
    lon = item["position"]["lng"]
    access = item.get("access", [])
    if access:
        access_lat = access[0].get("lat", lat)
        access_lon = access[0].get("lng", lon)
    else:
        access_lat, access_lon = lat, lon
    title = item.get("title", address)
    return (lat, lon, title, access_lat, access_lon)

def decode_poly(encoded):
    """Decodifica el FlexPolyline devuelto por HERE Routing v8."""
    try:
        decoded = fp.decode(encoded)
        # flexpolyline devuelve (lat, lon[, z]); nos quedamos solo con lat/lon
        return [(lat, lon) for lat, lon, *_rest in decoded]
    except Exception as e:
        raise ValueError("Invalid polyline") from e

def truck_route(origin, destination, apikey):
    base = "https://router.hereapi.com/v8/routes"
    params = {
        "transportMode": "truck",
        "origin": f"{origin[0]},{origin[1]}",
        "destination": f"{destination[0]},{destination[1]}",
        "return": "polyline,summary",
        "apikey": apikey,
    }
    params.update(TRUCK_PARAMS)
    r = requests.get(base, params=params, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Routing failed: {r.status_code} - {r.text}")
    data = r.json()
    if not data.get("routes"):
        raise ValueError("No route found.")
    route = data["routes"][0]["sections"][0]
    summary = route["summary"]
    length_m = summary["length"]
    duration_s = summary["duration"]
    poly = route["polyline"]
    coords = decode_poly(poly)
    return coords, length_m, duration_s

def compute_tariff(distance_km):
    if distance_km <= ZONA_1_KM:
        return PRECIO_ZONA_1
    elif distance_km <= ZONA_2_KM:
        return PRECIO_ZONA_2
    elif distance_km <= ZONA_3_KM:
        return PRECIO_ZONA_3
    elif distance_km <= ZONA_4_KM:
        return PRECIO_ZONA_4
    else:
        km_extra = distance_km - ZONA_4_KM
        return PRECIO_ZONA_4 + km_extra * PRECIO_POR_KM_EXTRA

def human_duration(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"

def add_zone_circles(m, center_lat, center_lon):
    Circle(radius=ZONA_1_KM * 1000, location=[center_lat, center_lon], color="green",
           fill=True, fill_opacity=0.10, tooltip=f"Zona 1 (≤{ZONA_1_KM} km): {PRECIO_ZONA_1} €").add_to(m)
    Circle(radius=ZONA_2_KM * 1000, location=[center_lat, center_lon], color="orange",
           fill=True, fill_opacity=0.10, tooltip=f"Zona 2 (≤{ZONA_2_KM} km): {PRECIO_ZONA_2} €").add_to(m)
    Circle(radius=ZONA_3_KM * 1000, location=[center_lat, center_lon], color="blue",
           fill=True, fill_opacity=0.05, tooltip=f"Zona 3 (≤{ZONA_3_KM} km): {PRECIO_ZONA_3} €").add_to(m)
    Circle(radius=ZONA_4_KM * 1000, location=[center_lat, center_lon], color="purple",
           fill=True, fill_opacity=0.05, tooltip=f"Zona 4 (≤{ZONA_4_KM} km): {PRECIO_ZONA_4} €").add_to(m)

def legend_html():
    return f"""
    <div style="position: fixed; bottom: 25px; left: 25px; width: 260px;
    border:2px solid #888; background: white; z-index:9999; font-size:14px; padding:8px;">
    <b>Tarifas</b><br>
    Zona 1 (≤{ZONA_1_KM} km): {PRECIO_ZONA_1} €<br>
    Zona 2 (≤{ZONA_2_KM} km): {PRECIO_ZONA_2} €<br>
    Zona 3 (≤{ZONA_3_KM} km): {PRECIO_ZONA_3} €<br>
    Zona 4 (≤{ZONA_4_KM} km): {PRECIO_ZONA_4} €<br>
    +{PRECIO_POR_KM_EXTRA} €/km extra a partir de {ZONA_4_KM} km
    </div>
    """

def madrid_now_iso():
    if ZoneInfo is not None:
        tz = ZoneInfo("Europe/Madrid")
        return datetime.now(tz).isoformat(timespec="seconds")
    return datetime.now().isoformat(timespec="seconds")

# =========================================================
# Logging automático a Google Sheets
# =========================================================
def append_to_gsheet(spreadsheet_key: str, worksheet_name: str, row: dict):
    gc = sheets_client_from_secrets()
    sh = gc.open_by_key(spreadsheet_key)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=1, cols=len(FIELDNAMES))
        ws.append_row(FIELDNAMES, value_input_option="RAW")
    header = ws.row_values(1)
    if not header:
        ws.append_row(FIELDNAMES, value_input_option="RAW")
    values = [row.get(k, "") for k in FIELDNAMES]
    ws.append_row(values, value_input_option="USER_ENTERED")

def log_to_sheets(row: dict):
    logs_sheet_id = st.secrets.get("LOGS_SHEET_ID", "")
    if not logs_sheet_id:
        return False, "Falta 'LOGS_SHEET_ID' en Secrets."
    if not _gspread_ready:
        return False, "Faltan dependencias gspread/google-auth."
    try:
        append_to_gsheet(logs_sheet_id, "logs", row)
        return True, None
    except Exception as e:
        return False, str(e)

# =========================================================
# INTERFAZ
# =========================================================
st.set_page_config(page_title="Cálculo de porte (camión)", layout="wide")
st.title("🚚 Cálculo de porte por ruta (HERE)")

api_key = get_api_key()
if not api_key:
    st.warning("Configura tu HERE_API_KEY en **st.secrets** o variable de entorno HERE_API_KEY.")

with st.sidebar:
    st.header("⚙️ Configuración")

    st.subheader("Origen (fijo)")
    st.text_input("Dirección de origen", value=ORIGIN_ADDRESS, disabled=True)
    col_o1, col_o2 = st.columns(2)
    with col_o1:
        st.number_input("Origen lat", value=ORIGIN_LAT, format="%.6f", disabled=True)
    with col_o2:
        st.number_input("Origen lon", value=ORIGIN_LON, format="%.6f", disabled=True)

    st.markdown("---")
    st.subheader("Datos del porte")
    cliente_nombre = st.text_input("Nombre del cliente", value="")
    operario_codigo = st.text_input("Código de operario", value="")

    st.markdown("---")
    st.subheader("Destino")
    dest_address = st.text_input("Dirección destino", value="Calle Alcalá 100")
    dest_postal = st.text_input("Código postal (opcional)", value="")
    dest_city = st.text_input("Población (opcional)", value="Madrid")

    st.markdown("---")
    st.subheader("Tarifas (solo lectura)")
    if REMOTE_CFG:
        st.caption("Cargadas desde la hoja de control. Para cambiarlas, edita esa hoja, no la app.")
    else:
        st.caption("⚠️ No se pudo leer la hoja de control: se están usando los valores por defecto del código.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.number_input("Zona 1 (km)", value=ZONA_1_KM, step=1, disabled=True)
        st.number_input("Zona 2 (km)", value=ZONA_2_KM, step=1, disabled=True)
    with col_b:
        st.number_input("Zona 3 (km)", value=ZONA_3_KM, step=1, disabled=True)
        st.number_input("Zona 4 (km)", value=ZONA_4_KM, step=1, disabled=True)

    st.number_input("Precio Zona 1 (€)", value=PRECIO_ZONA_1, step=1, disabled=True)
    st.number_input("Precio Zona 2 (€)", value=PRECIO_ZONA_2, step=1, disabled=True)
    st.number_input("Precio Zona 3 (€)", value=PRECIO_ZONA_3, step=1, disabled=True)
    st.number_input("Precio Zona 4 (€)", value=PRECIO_ZONA_4, step=1, disabled=True)
    st.number_input("€ por km extra (a partir de Zona 4)", value=float(PRECIO_POR_KM_EXTRA), step=0.1, disabled=True)

    # Nota: ZONA_*_KM y PRECIO_* ya NO se reasignan desde el sidebar.
    # Los únicos valores que se usan en el cálculo son los que vienen de
    # REMOTE_CFG (hoja de control) o, en su defecto, las constantes del código.

    st.markdown("---")
    logs_ok = bool(st.secrets.get("LOGS_SHEET_ID", ""))
    if logs_ok:
        st.caption("📝 Los cálculos se registran automáticamente en Google Sheets.")
    else:
        st.caption("⚠️ Registro en Sheets desactivado: falta 'LOGS_SHEET_ID' en Secrets.")

    if REMOTE_CONTROL_ID:
        with st.expander("🔧 Configuración remota (debug)"):
            st.write("CONTROL_SHEET_ID:", REMOTE_CONTROL_ID)
            st.json(REMOTE_CFG)

    go = st.button("Calcular ruta y precio", type="primary")

map_col, info_col = st.columns([2, 1])

if go:
    if not api_key:
        st.error("Falta HERE_API_KEY. Añádelo en la sección de secretos o como variable de entorno.")
        st.stop()

    if not cliente_nombre.strip() or not operario_codigo.strip():
        st.error("Introduce el nombre del cliente y el código de operario antes de calcular.")
        st.stop()

    with st.spinner("Geocodificando dirección de destino..."):
        try:
            dlat, dlon, dtitle, dacc_lat, dacc_lon = geocode_address(
                dest_address, api_key, postal_code=dest_postal or None, city=dest_city or None
            )
            dest = (dacc_lat, dacc_lon, dtitle)
        except Exception as e:
            st.error(f"Error geocodificando: {e}")
            st.stop()

    with st.spinner("Calculando ruta para camión..."):
        try:
            coords, length_m, duration_s = truck_route(
                (ORIGIN_LAT, ORIGIN_LON), (dest[0], dest[1]), api_key
            )
        except Exception as e:
            st.error(f"Error calculando ruta: {e}")
            st.stop()

    distancia_km = round(length_m / 1000.0, 2)
    dur = human_duration(duration_s)
    price = compute_tariff(distancia_km)

    row = {
        "timestamp_iso": madrid_now_iso(),
        "cliente_nombre": cliente_nombre.strip(),
        "operario_codigo": operario_codigo.strip(),
        "origin_address": ORIGIN_ADDRESS,
        "origin_lat": ORIGIN_LAT,
        "origin_lon": ORIGIN_LON,
        "dest_input_address": dest_address,
        "dest_input_postal": dest_postal,
        "dest_input_city": dest_city,
        "dest_geocoded_title": dest[2],
        "dest_lat": dest[0],
        "dest_lon": dest[1],
        "distance_km": distancia_km,
        "duration_seconds": int(duration_s),
        "duration_human": dur,
        "price_eur": round(price, 2),
        "zona_1_km": ZONA_1_KM, "zona_2_km": ZONA_2_KM, "zona_3_km": ZONA_3_KM, "zona_4_km": ZONA_4_KM,
        "precio_z1": PRECIO_ZONA_1, "precio_z2": PRECIO_ZONA_2, "precio_z3": PRECIO_ZONA_3, "precio_z4": PRECIO_ZONA_4,
        "precio_km_extra": PRECIO_POR_KM_EXTRA,
        "truck_height": TRUCK_PARAMS.get("truck[height]"),
        "truck_width": TRUCK_PARAMS.get("truck[width]"),
        "truck_length": TRUCK_PARAMS.get("truck[length]"),
        "truck_gross_weight": TRUCK_PARAMS.get("truck[grossWeight]"),
        "truck_axle_count": TRUCK_PARAMS.get("truck[axleCount]"),
        "truck_type": TRUCK_PARAMS.get("truck[type]"),
    }

    # Registro automático (una sola vez, en el momento del cálculo)
    log_ok, log_err = log_to_sheets(row)

    # Persistimos el resultado para que sobreviva a los reruns del mapa
    st.session_state["result"] = {
        "cliente_nombre": cliente_nombre.strip(),
        "operario_codigo": operario_codigo.strip(),
        "dest": dest,
        "coords": coords,
        "distancia_km": distancia_km,
        "dur": dur,
        "price": price,
        "log_ok": log_ok,
        "log_err": log_err,
    }

result = st.session_state.get("result")

if result:
    with info_col:
        st.subheader("Resultado")
        st.metric("Distancia (km)", result["distancia_km"])
        st.metric("Duración", result["dur"])
        st.metric("Precio (€)", f"{result['price']:.2f}")
        st.caption(f"Cliente: **{result['cliente_nombre']}**")
        st.caption(f"Operario: **{result['operario_codigo']}**")
        st.caption(f"Destino: **{result['dest'][2]}**")
        st.caption(f"Origen: **{ORIGIN_ADDRESS}**")

        if result["log_ok"]:
            st.success("Registrado en Google Sheets ✅")
        elif result["log_err"]:
            st.warning(f"No se pudo registrar en Sheets: {result['log_err']}")

    with map_col:
        m = Map(location=[ORIGIN_LAT, ORIGIN_LON], zoom_start=12, control_scale=True)
        add_zone_circles(m, ORIGIN_LAT, ORIGIN_LON)
        Marker([ORIGIN_LAT, ORIGIN_LON], tooltip="Almacén (origen)", icon=folium.Icon(color="blue")).add_to(m)
        Marker([result["dest"][0], result["dest"][1]], tooltip=result["dest"][2], icon=folium.Icon(color="red")).add_to(m)
        PolyLine(locations=result["coords"], weight=5, opacity=0.8).add_to(m)
        m.get_root().html.add_child(Element(legend_html()))
        st_folium(m, width=None, height=600)
else:
    with map_col:
        m = Map(location=[ORIGIN_LAT, ORIGIN_LON], zoom_start=12, control_scale=True)
        add_zone_circles(m, ORIGIN_LAT, ORIGIN_LON)
        Marker([ORIGIN_LAT, ORIGIN_LON], tooltip="Almacén (origen)", icon=folium.Icon(color="blue")).add_to(m)
        m.get_root().html.add_child(Element(legend_html()))
        st_folium(m, width=None, height=600)

    with info_col:
        st.info("Introduce un destino en la barra lateral y pulsa **Calcular ruta y precio**.")
