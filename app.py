
import os
import csv
import time
import math
import requests
import streamlit as st
import folium
from folium import Map, Marker, Circle, PolyLine, Element
from streamlit_folium import st_folium
import polyline as pl
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

def get_api_key():
    if "HERE_API_KEY" in st.secrets:
        return st.secrets["HERE_API_KEY"]
    env_key = os.getenv("HERE_API_KEY")
    if env_key:
        return env_key
    return None

DEFAULT_ORIGIN_ADDRESS = "C. de Servando Batanero, 67, 28017 Madrid"
DEFAULT_ORIGIN_LAT = 40.437869
DEFAULT_ORIGIN_LON = -3.646404

ZONA_1_KM = 3
ZONA_2_KM = 5
ZONA_3_KM = 10
ZONA_4_KM = 20

PRECIO_ZONA_1 = 25
PRECIO_ZONA_2 = 35
PRECIO_ZONA_3 = 50
PRECIO_ZONA_4 = 70
PRECIO_POR_KM_EXTRA = 1

TRUCK_PARAMS = {
    "truckHeight": 4,
    "truckWidth": 2.5,
    "truckLength": 10,
    "truckWeight": 16000,
    "truckAxleCount": 2,
    "truckType": "delivery"
}

FIELDNAMES = [
    "timestamp_iso",
    "origin_address","origin_lat","origin_lon",
    "dest_input_address","dest_input_postal","dest_input_city",
    "dest_geocoded_title","dest_lat","dest_lon",
    "distance_km","duration_seconds","duration_human","price_eur",
    "zona_1_km","zona_2_km","zona_3_km","zona_4_km",
    "precio_z1","precio_z2","precio_z3","precio_z4","precio_km_extra",
    "truckHeight","truckWidth","truckLength","truckWeight","truckAxleCount","truckType"
]

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
    try:
        return pl.decode(encoded, precision=6)
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
        km_extra = distance_km - ZONA_2_KM
        return PRECIO_ZONA_4 + km_extra * PRECIO_POR_KM_EXTRA

def human_duration(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h: return f"{h}h {m}m {s}s"
    if m: return f"{m}m {s}s"
    return f"{s}s"

def add_zone_circles(m, center_lat, center_lon):
    Circle(radius=ZONA_1_KM*1000, location=[center_lat, center_lon], color="green",
           fill=True, fill_opacity=0.10, tooltip=f"Zona 1 (≤{ZONA_1_KM} km): {PRECIO_ZONA_1} €").add_to(m)
    Circle(radius=ZONA_2_KM*1000, location=[center_lat, center_lon], color="orange",
           fill=True, fill_opacity=0.10, tooltip=f"Zona 2 (≤{ZONA_2_KM} km): {PRECIO_ZONA_2} €").add_to(m)
    Circle(radius=ZONA_3_KM*1000, location=[center_lat, center_lon], color="blue",
           fill=True, fill_opacity=0.05, tooltip=f"Zona 3 (≤{ZONA_3_KM} km): {PRECIO_ZONA_3} €").add_to(m)
    Circle(radius=ZONA_4_KM*1000, location=[center_lat, center_lon], color="purple",
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
    +{PRECIO_POR_KM_EXTRA} €/km extra a partir de {ZONA_2_KM} km
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
        filtered = {k: row.get(k, "") for k in FIELDNAMES}
        writer.writerow(filtered)

def sheets_client_from_secrets():
    if not _gspread_ready:
        raise RuntimeError("gspread/google-auth no están instalados.")
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Falta 'gcp_service_account' en st.secrets.")
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SHEETS_SCOPES)
    gc = gspread.authorize(creds)
    return gc

def append_to_gsheet(spreadsheet_key: str, worksheet_name: str, row: dict):
    gc = sheets_client_from_secrets()
    sh = gc.open_by_key(spreadsheet_key)
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=1, cols=len(FIELDNAMES))
        ws.append_row(FIELDNAMES, value_input_option="RAW")
    # Ensure header exists
    header = ws.row_values(1)
    if not header:
        ws.append_row(FIELDNAMES, value_input_option="RAW")
    values = [row.get(k, "") for k in FIELDNAMES]
    ws.append_row(values, value_input_option="USER_ENTERED")

st.set_page_config(page_title="Cálculo de porte (camión)", layout="wide")
st.title("🚚 Cálculo de porte por ruta (HERE)")

api_key = get_api_key()
if not api_key:
    st.warning("Configura tu HERE_API_KEY en **st.secrets** o variable de entorno HERE_API_KEY.")

with st.sidebar:
    st.header("⚙️ Configuración")
    origin_address = st.text_input("Dirección de origen", value=DEFAULT_ORIGIN_ADDRESS)
    origin_lat = st.number_input("Origen lat", value=DEFAULT_ORIGIN_LAT, format="%.6f")
    origin_lon = st.number_input("Origen lon", value=DEFAULT_ORIGIN_LON, format="%.6f")

    st.markdown("---")
    st.subheader("Destino")
    dest_address = st.text_input("Dirección destino", value="Calle Alcalá 100")
    dest_postal = st.text_input("Código postal (opcional)", value="")
    dest_city = st.text_input("Población (opcional)", value="Madrid")

    st.markdown("---")
    st.subheader("Tarifas")
    col_a, col_b = st.columns(2)
    with col_a:
        z1 = st.number_input("Zona 1 (km)", value=ZONA_1_KM, step=1)
        z2 = st.number_input("Zona 2 (km)", value=ZONA_2_KM, step=1)
    with col_b:
        z3 = st.number_input("Zona 3 (km)", value=ZONA_3_KM, step=1)
        z4 = st.number_input("Zona 4 (km)", value=ZONA_4_KM, step=1)

    p1 = st.number_input("Precio Zona 1 (€)", value=PRECIO_ZONA_1, step=1)
    p2 = st.number_input("Precio Zona 2 (€)", value=PRECIO_ZONA_2, step=1)
    p3 = st.number_input("Precio Zona 3 (€)", value=PRECIO_ZONA_3, step=1)
    p4 = st.number_input("Precio Zona 4 (€)", value=PRECIO_ZONA_4, step=1)
    pextra = st.number_input("€ por km extra", value=PRECIO_POR_KM_EXTRA, step=1.0)

    st.markdown("---")
    st.subheader("Registro en CSV")
    log_csv = st.checkbox("Registrar cálculos en CSV", value=True)
    csv_path = st.text_input("Ruta del CSV", value="logs/calculos_portes.csv")

    st.markdown("---")
    st.subheader("Subir a Google Sheets")
    gs_enable = st.checkbox("Activar subida a Google Sheets", value=False)
    spreadsheet_key = st.text_input("Spreadsheet key (ID)", value="")
    worksheet_name = st.text_input("Nombre de hoja (worksheet)", value="logs")

  
    ZONA_1_KM, ZONA_2_KM, ZONA_3_KM, ZONA_4_KM = int(z1), int(z2), int(z3), int(z4)
    PRECIO_ZONA_1, PRECIO_ZONA_2, PRECIO_ZONA_3, PRECIO_ZONA_4, PRECIO_POR_KM_EXTRA = int(p1), int(p2), int(p3), int(p4), float(pextra)

    go = st.button("Calcular ruta y precio", type="primary")

map_col, info_col = st.columns([2, 1])

if go:
    if not api_key:
        st.error("Falta HERE_API_KEY. Añádelo en la sección de secretos o como variable de entorno.")
        st.stop()
    with st.spinner("Geocodificando direcciones..."):
        try:
            orig = (origin_lat, origin_lon, origin_address, origin_lat, origin_lon)
            dlat, dlon, dtitle, dacc_lat, dacc_lon = geocode_address(dest_address, api_key, postal_code=dest_postal or None, city=dest_city or None)
            dest = (dacc_lat, dacc_lon, dtitle)
        except Exception as e:
            st.error(f"Error geocodificando: {e}")
            st.stop()

    with st.spinner("Calculando ruta para camión..."):
        try:
            coords, length_m, duration_s = truck_route((origin_lat, origin_lon), (dest[0], dest[1]), api_key)
        except Exception as e:
            st.error(f"Error calculando ruta: {e}")
            st.stop()

    distancia_km = round(length_m / 1000.0, 2)
    dur = human_duration(duration_s)
    price = compute_tariff(distancia_km)

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
        "zona_1_km": ZONA_1_KM, "zona_2_km": ZONA_2_KM, "zona_3_km": ZONA_3_KM, "zona_4_km": ZONA_4_KM,
        "precio_z1": PRECIO_ZONA_1, "precio_z2": PRECIO_ZONA_2, "precio_z3": PRECIO_ZONA_3, "precio_z4": PRECIO_ZONA_4,
        "precio_km_extra": PRECIO_POR_KM_EXTRA,
        "truckHeight": TRUCK_PARAMS.get("truckHeight"),
        "truckWidth": TRUCK_PARAMS.get("truckWidth"),
        "truckLength": TRUCK_PARAMS.get("truckLength"),
        "truckWeight": TRUCK_PARAMS.get("truckWeight"),
        "truckAxleCount": TRUCK_PARAMS.get("truckAxleCount"),
        "truckType": TRUCK_PARAMS.get("truckType"),
    }

    with info_col:
        st.subheader("Resultado")
        st.metric("Distancia (km)", distancia_km)
        st.metric("Duración", dur)
        st.metric("Precio (€)", f"{price:.2f}")
        st.caption(f"Destino: **{dest[2]}**")
        st.caption(f"Origen: **{origin_address}**")

        if log_csv:
            try:
                log_to_csv(csv_path, row)
                st.success(f"Guardado en CSV: {csv_path}")
            except Exception as e:
                st.warning(f"No se pudo registrar en CSV ({csv_path}): {e}")

        if gs_enable:
            try:
                if not _gspread_ready:
                    st.error("Faltan dependencias gspread/google-auth (instálalas).")
                elif not spreadsheet_key.strip():
                    st.error("Debes indicar el Spreadsheet key (ID).")
                else:
                    append_to_gsheet(spreadsheet_key.strip(), worksheet_name.strip() or "logs", row)
                    st.success("Fila añadida a Google Sheets ✅")
                    st.caption("Si ves 'PERMISSION_DENIED', comparte el Sheet con el Service Account.")
            except Exception as e:
                st.warning(f"No se pudo subir a Google Sheets: {e}")

    with map_col:
        m = Map(location=[origin_lat, origin_lon], zoom_start=12, control_scale=True)
        add_zone_circles(m, origin_lat, origin_lon)
        Marker([origin_lat, origin_lon], tooltip="Almacén (origen)", icon=folium.Icon(color="blue")).add_to(m)
        Marker([dest[0], dest[1]], tooltip=dest[2], icon=folium.Icon(color="red")).add_to(m)
        PolyLine(locations=coords, weight=5, opacity=0.8).add_to(m)
        m.get_root().html.add_child(Element(legend_html()))
        st_folium(m, width=None, height=600)
else:
    with map_col:
        m = Map(location=[DEFAULT_ORIGIN_LAT, DEFAULT_ORIGIN_LON], zoom_start=12, control_scale=True)
        add_zone_circles(m, DEFAULT_ORIGIN_LAT, DEFAULT_ORIGIN_LON)
        Marker([DEFAULT_ORIGIN_LAT, DEFAULT_ORIGIN_LON], tooltip="Almacén (origen)", icon=folium.Icon(color="blue")).add_to(m)
        m.get_root().html.add_child(Element(legend_html()))
        st_folium(m, width=None, height=600)

    with info_col:
        st.info("Introduce un destino en la barra lateral y pulsa **Calcular ruta y precio**.")
