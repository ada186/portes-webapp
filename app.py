import os
import csv
import requests
import streamlit as st
import folium
from folium import Map, Marker, Circle, PolyLine, Element
from streamlit_folium import st_folium
import polyline as pl
from datetime import datetime

# ---- Zona horaria ----
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

# ================================================================
# CONFIGURACIÓN POR DEFECTO (fallback si Google Sheets no está)
# ================================================================
DEFAULT_ORIGIN_ADDRESS = "C. de Servando Batanero, 67, 28017 Madrid"
DEFAULT_ORIGIN_LAT = 40.42995450669478
DEFAULT_ORIGIN_LON = -3.644614746858031

ZONA_1_KM = 3
ZONA_2_KM = 5
ZONA_3_KM = 10
ZONA_4_KM = 20

PRECIO_ZONA_1 = 25
PRECIO_ZONA_2 = 35
PRECIO_ZONA_3 = 50
PRECIO_ZONA_4 = 70
PRECIO_POR_KM_EXTRA = 1.0

# CORRECCIÓN: formato correcto para HERE Routing API v8
TRUCK_PARAMS = {
    "truck[height]": 400,        # cm
    "truck[width]": 250,         # cm
    "truck[length]": 1000,       # cm
    "truck[grossWeight]": 16000, # kg
    "truck[axleCount]": 2,
    "truck[type]": "straight",
}

FIELDNAMES = [
    "timestamp_iso",
    "origin_address", "origin_lat", "origin_lon",
    "dest_input_address", "dest_input_postal", "dest_input_city",
    "dest_geocoded_title", "dest_lat", "dest_lon",
    "distance_km", "duration_seconds", "duration_human", "price_eur",
    "zona_1_km", "zona_2_km", "zona_3_km", "zona_4_km",
    "precio_z1", "precio_z2", "precio_z3", "precio_z4", "precio_km_extra",
    "truckHeight", "truckWidth", "truckLength", "truckWeight", "truckAxleCount", "truckType",
]

# ================================================================
# CONFIGURACIÓN REMOTA DESDE GOOGLE SHEETS (opcional)
# ================================================================
def sheets_client_from_secrets():
    """Crea cliente gspread desde Streamlit Secrets."""
    if not _gspread_ready:
        raise RuntimeError("gspread/google-auth no están instalados.")
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Falta 'gcp_service_account' en st.secrets.")
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SHEETS_SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def load_remote_config(control_sheet_id: str) -> dict:
    """Lee pares key/value de la pestaña 'config' en la hoja de control."""
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

def get_remote_config() -> dict:
    """Intenta cargar la configuración remota. Devuelve {} si no está disponible."""
    control_id = st.secrets.get("CONTROL_SHEET_ID", "")
    if not control_id or not _gspread_ready:
        return {}
    try:
        return load_remote_config(control_id)
    except Exception:
        return {}

def cfg_float(cfg: dict, key: str, default: float) -> float:
    try:
        return float(cfg[key])
    except (KeyError, ValueError, TypeError):
        return default

def cfg_int(cfg: dict, key: str, default: int) -> int:
    try:
        return int(float(cfg[key]))
    except (KeyError, ValueError, TypeError):
        return default

# ================================================================
# FUNCIONES DE NEGOCIO
# ================================================================
def get_api_key():
    if "HERE_API_KEY" in st.secrets:
        return st.secrets["HERE_API_KEY"]
    return os.getenv("HERE_API_KEY")

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
        raise ValueError("No se encontraron resultados para esa dirección.")
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
    try:
        return pl.decode(encoded, precision=6)
    except Exception as e:
        raise ValueError("Polyline inválida") from e

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
        raise ValueError("No se encontró ninguna ruta.")
    route = data["routes"][0]["sections"][0]
    summary = route["summary"]
    coords = decode_poly(route["polyline"])
    return coords, summary["length"], summary["duration"]

def compute_tariff(distance_km, z1, z2, z3, z4, p1, p2, p3, p4, pextra):
    if distance_km <= z1:
        return p1
    elif distance_km <= z2:
        return p2
    elif distance_km <= z3:
        return p3
    elif distance_km <= z4:
        return p4
    else:
        # CORRECCIÓN: km extra se cuentan desde el límite de la zona 4
        km_extra = distance_km - z4
        return p4 + km_extra * pextra

def human_duration(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h: return f"{h}h {m}m {s}s"
    if m: return f"{m}m {s}s"
    return f"{s}s"

def add_zone_circles(m, center_lat, center_lon, z1, z2, z3, z4, p1, p2, p3, p4):
    Circle(radius=z1*1000, location=[center_lat, center_lon], color="green",
           fill=True, fill_opacity=0.10, tooltip=f"Zona 1 (≤{z1} km): {p1} €").add_to(m)
    Circle(radius=z2*1000, location=[center_lat, center_lon], color="orange",
           fill=True, fill_opacity=0.10, tooltip=f"Zona 2 (≤{z2} km): {p2} €").add_to(m)
    Circle(radius=z3*1000, location=[center_lat, center_lon], color="blue",
           fill=True, fill_opacity=0.05, tooltip=f"Zona 3 (≤{z3} km): {p3} €").add_to(m)
    Circle(radius=z4*1000, location=[center_lat, center_lon], color="purple",
           fill=True, fill_opacity=0.05, tooltip=f"Zona 4 (≤{z4} km): {p4} €").add_to(m)

def legend_html(z1, z2, z3, z4, p1, p2, p3, p4, pextra):
    return f"""
    <div style="position: fixed; bottom: 25px; left: 25px; width: 270px;
    border:2px solid #888; background: white; z-index:9999; font-size:14px; padding:10px; border-radius:6px;">
    <b>Tarifas</b><br>
    🟢 Zona 1 (≤{z1} km): {p1} €<br>
    🟠 Zona 2 (≤{z2} km): {p2} €<br>
    🔵 Zona 3 (≤{z3} km): {p3} €<br>
    🟣 Zona 4 (≤{z4} km): {p4} €<br>
    +{pextra} €/km extra a partir de {z4} km
    </div>
    """

def madrid_now_iso():
    if ZoneInfo is not None:
        tz = ZoneInfo("Europe/Madrid")
        return datetime.now(tz).isoformat(timespec="seconds")
    return datetime.now().isoformat(timespec="seconds")

def ensure_parent_dir(path: str):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

def log_to_csv(csv_path: str, row: dict):
    ensure_parent_dir(csv_path)
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in FIELDNAMES})

def append_to_gsheet(spreadsheet_key: str, worksheet_name: str, row: dict):
    gc = sheets_client_from_secrets()
    sh = gc.open_by_key(spreadsheet_key)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=1, cols=len(FIELDNAMES))
        ws.append_row(FIELDNAMES, value_input_option="RAW")
    if not ws.row_values(1):
        ws.append_row(FIELDNAMES, value_input_option="RAW")
    ws.append_row([row.get(k, "") for k in FIELDNAMES], value_input_option="USER_ENTERED")

# ================================================================
# INTERFAZ
# ================================================================
st.set_page_config(page_title="Cálculo de porte (camión)", layout="wide")
st.title("🚚 Cálculo de porte por ruta (HERE)")

api_key = get_api_key()
if not api_key:
    st.warning("Configura tu HERE_API_KEY en **st.secrets** o como variable de entorno HERE_API_KEY.")

# Cargar configuración remota (silencioso si no está disponible)
REMOTE_CFG = get_remote_config()

with st.sidebar:
    st.header("⚙️ Configuración")
    st.caption(f"📍 Origen fijo: {DEFAULT_ORIGIN_ADDRESS}")

    # Coordenadas del origen verificadas manualmente — nunca se geocodifica
    # para evitar que HERE lo resuelva a un punto incorrecto.
    origin_lat = DEFAULT_ORIGIN_LAT
    origin_lon = DEFAULT_ORIGIN_LON
    origin_address = DEFAULT_ORIGIN_ADDRESS

    st.markdown("---")
    st.subheader("Destino")
    dest_address = st.text_input("Dirección destino", value="Calle Alcalá 100")
    dest_postal = st.text_input("Código postal (opcional)", value="")
    dest_city = st.text_input("Población (opcional)", value="Madrid")

    st.markdown("---")
    st.subheader("Tarifas")
    # Usar valores remotos si están disponibles, si no los hardcodeados
    col_a, col_b = st.columns(2)
    with col_a:
        z1 = st.number_input("Zona 1 (km)", value=cfg_int(REMOTE_CFG, "zona_1_km", ZONA_1_KM), step=1)
        z2 = st.number_input("Zona 2 (km)", value=cfg_int(REMOTE_CFG, "zona_2_km", ZONA_2_KM), step=1)
    with col_b:
        z3 = st.number_input("Zona 3 (km)", value=cfg_int(REMOTE_CFG, "zona_3_km", ZONA_3_KM), step=1)
        z4 = st.number_input("Zona 4 (km)", value=cfg_int(REMOTE_CFG, "zona_4_km", ZONA_4_KM), step=1)

    p1 = st.number_input("Precio Zona 1 (€)", value=cfg_int(REMOTE_CFG, "precio_z1", PRECIO_ZONA_1), step=1)
    p2 = st.number_input("Precio Zona 2 (€)", value=cfg_int(REMOTE_CFG, "precio_z2", PRECIO_ZONA_2), step=1)
    p3 = st.number_input("Precio Zona 3 (€)", value=cfg_int(REMOTE_CFG, "precio_z3", PRECIO_ZONA_3), step=1)
    p4 = st.number_input("Precio Zona 4 (€)", value=cfg_int(REMOTE_CFG, "precio_z4", PRECIO_ZONA_4), step=1)
    pextra = st.number_input("€/km extra", value=cfg_float(REMOTE_CFG, "precio_km_extra", float(PRECIO_POR_KM_EXTRA)), step=0.1)

    if REMOTE_CFG:
        st.caption("✅ Tarifas cargadas desde Google Sheets")

    st.markdown("---")
    st.subheader("Registro en CSV")
    log_csv = st.checkbox("Registrar cálculos en CSV", value=True)
    csv_path = st.text_input("Ruta del CSV", value="logs/calculos_portes.csv")

    st.markdown("---")
    st.subheader("Subir a Google Sheets")
    gs_enable = st.checkbox("Activar subida a Google Sheets", value=False)
    spreadsheet_key = st.text_input(
        "Spreadsheet key (ID)",
        value=REMOTE_CFG.get("spreadsheet_key", "")
    )
    worksheet_name = st.text_input(
        "Nombre de hoja (worksheet)",
        value=REMOTE_CFG.get("worksheet_name", "logs")
    )

    go = st.button("Calcular ruta y precio", type="primary")

# ================================================================
# SESSION STATE — los resultados persisten entre recargas
# ================================================================
if "resultado" not in st.session_state:
    st.session_state.resultado = None

if go:
    if not api_key:
        st.error("Falta HERE_API_KEY.")
        st.stop()

    with st.spinner("Geocodificando dirección de destino..."):
        try:
            dlat, dlon, dtitle, dacc_lat, dacc_lon = geocode_address(
                dest_address, api_key,
                postal_code=dest_postal or None,
                city=dest_city or None
            )
            dest = (dacc_lat, dacc_lon, dtitle)
        except Exception as e:
            st.error(f"Error geocodificando: {e}")
            st.stop()

    with st.spinner("Calculando ruta para camión..."):
        try:
            coords, length_m, duration_s = truck_route(
                (origin_lat, origin_lon), (dest[0], dest[1]), api_key
            )
        except Exception as e:
            st.error(f"Error calculando ruta: {e}")
            st.stop()

    distancia_km = round(length_m / 1000.0, 2)
    dur = human_duration(duration_s)
    price = compute_tariff(
        distancia_km,
        int(z1), int(z2), int(z3), int(z4),
        int(p1), int(p2), int(p3), int(p4), float(pextra)
    )

    row = {
        "timestamp_iso": madrid_now_iso(),
        "origin_address": origin_address,
        "origin_lat": origin_lat,
        "origin_lon": origin_lon,
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
        "zona_1_km": int(z1), "zona_2_km": int(z2), "zona_3_km": int(z3), "zona_4_km": int(z4),
        "precio_z1": int(p1), "precio_z2": int(p2), "precio_z3": int(p3), "precio_z4": int(p4),
        "precio_km_extra": float(pextra),
        "truckHeight": 4, "truckWidth": 2.5, "truckLength": 10,
        "truckWeight": 16000, "truckAxleCount": 2, "truckType": "straight",
    }

    # Guardar en session_state para que persista
    st.session_state.resultado = {
        "dest": dest,
        "coords": coords,
        "distancia_km": distancia_km,
        "dur": dur,
        "price": price,
        "row": row,
        "origin_lat": origin_lat,
        "origin_lon": origin_lon,
        "origin_address": origin_address,
        "z1": int(z1), "z2": int(z2), "z3": int(z3), "z4": int(z4),
        "p1": int(p1), "p2": int(p2), "p3": int(p3), "p4": int(p4),
        "pextra": float(pextra),
    }

    # Logs (solo se ejecutan una vez al calcular, no en cada recarga)
    if log_csv:
        try:
            log_to_csv(csv_path, row)
        except Exception as e:
            st.warning(f"No se pudo registrar en CSV: {e}")

    if gs_enable:
        if not _gspread_ready:
            st.error("Faltan dependencias gspread/google-auth.")
        elif not spreadsheet_key.strip():
            st.error("Indica el Spreadsheet key (ID).")
        else:
            try:
                append_to_gsheet(spreadsheet_key.strip(), worksheet_name.strip() or "logs", row)
                st.success("✅ Fila añadida a Google Sheets")
            except Exception as e:
                st.warning(f"No se pudo subir a Google Sheets: {e}")

# ================================================================
# RENDERIZADO — usa session_state si hay resultado, si no muestra mapa vacío
# ================================================================
map_col, info_col = st.columns([2, 1])
res = st.session_state.resultado

if res:
    with info_col:
        st.subheader("Resultado")
        st.metric("Distancia (km)", res["distancia_km"])
        st.metric("Duración estimada", res["dur"])
        st.metric("Precio (€)", f"{res['price']:.2f} €")
        st.caption(f"📍 Destino: **{res['dest'][2]}**")
        st.caption(f"🏭 Origen: **{res['origin_address']}**")
        if log_csv and go:
            st.success(f"✅ Guardado en CSV: {csv_path}")

    with map_col:
        m = Map(location=[res["origin_lat"], res["origin_lon"]], zoom_start=12, control_scale=True)
        add_zone_circles(
            m, res["origin_lat"], res["origin_lon"],
            res["z1"], res["z2"], res["z3"], res["z4"],
            res["p1"], res["p2"], res["p3"], res["p4"]
        )
        Marker(
            [res["origin_lat"], res["origin_lon"]],
            tooltip="Almacén (origen)", icon=folium.Icon(color="blue")
        ).add_to(m)
        Marker(
            [res["dest"][0], res["dest"][1]],
            tooltip=res["dest"][2], icon=folium.Icon(color="red")
        ).add_to(m)
        PolyLine(locations=res["coords"], weight=5, opacity=0.8).add_to(m)
        m.get_root().html.add_child(Element(
            legend_html(res["z1"], res["z2"], res["z3"], res["z4"],
                        res["p1"], res["p2"], res["p3"], res["p4"], res["pextra"])
        ))
        st_folium(m, width=None, height=600)

else:
    with map_col:
        m = Map(location=[DEFAULT_ORIGIN_LAT, DEFAULT_ORIGIN_LON], zoom_start=12, control_scale=True)
        add_zone_circles(
            m, DEFAULT_ORIGIN_LAT, DEFAULT_ORIGIN_LON,
            ZONA_1_KM, ZONA_2_KM, ZONA_3_KM, ZONA_4_KM,
            PRECIO_ZONA_1, PRECIO_ZONA_2, PRECIO_ZONA_3, PRECIO_ZONA_4
        )
        Marker(
            [DEFAULT_ORIGIN_LAT, DEFAULT_ORIGIN_LON],
            tooltip="Almacén (origen)", icon=folium.Icon(color="blue")
        ).add_to(m)
        m.get_root().html.add_child(Element(legend_html(
            ZONA_1_KM, ZONA_2_KM, ZONA_3_KM, ZONA_4_KM,
            PRECIO_ZONA_1, PRECIO_ZONA_2, PRECIO_ZONA_3, PRECIO_ZONA_4,
            PRECIO_POR_KM_EXTRA
        )))
        st_folium(m, width=None, height=600)

    with info_col:
        st.info("Introduce un destino en la barra lateral y pulsa **Calcular ruta y precio**.")
