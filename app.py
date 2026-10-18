import os
import math
import base64
import html
from pathlib import Path
import requests
import streamlit as st
import folium
from folium import Map, Marker, Circle, PolyLine, Element
from streamlit_folium import st_folium
import flexpolyline as fp
from datetime import datetime

st.set_page_config(
    page_title="Portes · BigMat Rodríguez", page_icon=":material/local_shipping:", layout="wide",
)

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
ZONA_1_KM = 0.6
ZONA_2_KM = 2
ZONA_3_KM = 3
ZONA_4_KM = 7
ZONA_5_KM = 10
ZONA_6_KM = 20
ZONA_7_KM = 30

PRECIO_ZONA_1 = 50
PRECIO_ZONA_2 = 60
PRECIO_ZONA_3 = 70
PRECIO_ZONA_4 = 80
PRECIO_ZONA_5 = 90
PRECIO_ZONA_6 = 100
PRECIO_ZONA_7 = 120
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

# =========================================================
# SECCIONES
# Cada porte se etiqueta con la sección que lo origina. Todos se guardan
# en la misma hoja "logs"; la columna "seccion" permite filtrarlos.
# =========================================================
SECCIONES = ["Exposición Vital Aza", "Almacén Ezequiel Solana"]

# Prefijos válidos del número de albarán según la sección.
ALBARAN_PREFIJOS = {
    "Exposición Vital Aza": ("A02", "T02"),
    "Almacén Ezequiel Solana": ("A01", "T01"),
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
    # Las columnas nuevas van al final para no descolocar las filas ya guardadas.
    "seccion", "fecha_porte", "anotaciones",
    "zona_5_km", "zona_6_km", "zona_7_km",
    "precio_z5", "precio_z6", "precio_z7",
    "cliente_telefono", "albaran", "operario_nombre",
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

def normalize_operario(codigo: str) -> str:
    """Normaliza el código de operario para comparar ("007" == "7", "ab1" == "AB1")."""
    codigo = codigo.strip().upper()
    if codigo.isdigit():
        codigo = codigo.lstrip("0") or "0"
    return codigo

@st.cache_data(ttl=300)
def load_operarios(control_sheet_id: str) -> dict:
    """Lee la pestaña 'operarios' de la hoja de control: código (col. A) → nombre (col. B)."""
    gc = sheets_client_from_secrets()
    ws = gc.open_by_key(control_sheet_id).worksheet("operarios")
    operarios = {}
    for r in ws.get_all_values():
        if len(r) >= 2 and r[0].strip() and r[1].strip():
            if r[0].strip().lower() in ("código", "codigo"):
                continue  # fila de títulos
            operarios[normalize_operario(r[0])] = r[1].strip()
    return operarios

def parse_num(value: str) -> float:
    """Convierte un número de la hoja, aceptando coma decimal ("0,5")."""
    value = value.strip()
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return float(value)

def cfg_int(cfg, key, default):
    try:
        return int(parse_num(cfg[key]))
    except Exception:
        return default

def cfg_float(cfg, key, default):
    try:
        return parse_num(cfg[key])
    except Exception:
        return default

REMOTE_CONTROL_ID = st.secrets.get("CONTROL_SHEET_ID", "")
REMOTE_CFG = {}
if REMOTE_CONTROL_ID:
    try:
        REMOTE_CFG = load_remote_config(REMOTE_CONTROL_ID)
    except Exception as e:
        st.sidebar.warning(f"No se pudo leer la hoja de control: {e}")

OPERARIOS = {}
if REMOTE_CONTROL_ID:
    try:
        OPERARIOS = load_operarios(REMOTE_CONTROL_ID)
    except Exception as e:
        st.sidebar.warning(f"No se pudo leer la pestaña 'operarios' de la hoja de control: {e}")

# La hoja de control (si existe) se usa como fuente de los valores por defecto.
ZONA_1_KM = cfg_float(REMOTE_CFG, "ZONA_1_KM", ZONA_1_KM)
ZONA_2_KM = cfg_float(REMOTE_CFG, "ZONA_2_KM", ZONA_2_KM)
ZONA_3_KM = cfg_float(REMOTE_CFG, "ZONA_3_KM", ZONA_3_KM)
ZONA_4_KM = cfg_float(REMOTE_CFG, "ZONA_4_KM", ZONA_4_KM)
ZONA_5_KM = cfg_float(REMOTE_CFG, "ZONA_5_KM", ZONA_5_KM)
ZONA_6_KM = cfg_float(REMOTE_CFG, "ZONA_6_KM", ZONA_6_KM)
ZONA_7_KM = cfg_float(REMOTE_CFG, "ZONA_7_KM", ZONA_7_KM)
PRECIO_ZONA_1 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_1", PRECIO_ZONA_1)
PRECIO_ZONA_2 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_2", PRECIO_ZONA_2)
PRECIO_ZONA_3 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_3", PRECIO_ZONA_3)
PRECIO_ZONA_4 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_4", PRECIO_ZONA_4)
PRECIO_ZONA_5 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_5", PRECIO_ZONA_5)
PRECIO_ZONA_6 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_6", PRECIO_ZONA_6)
PRECIO_ZONA_7 = cfg_int(REMOTE_CFG, "PRECIO_ZONA_7", PRECIO_ZONA_7)
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
    elif distance_km <= ZONA_5_KM:
        return PRECIO_ZONA_5
    elif distance_km <= ZONA_6_KM:
        return PRECIO_ZONA_6
    elif distance_km <= ZONA_7_KM:
        return PRECIO_ZONA_7
    else:
        km_extra = distance_km - ZONA_7_KM
        return PRECIO_ZONA_7 + km_extra * PRECIO_POR_KM_EXTRA

def human_duration(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"

def zonas():
    """Las siete zonas vigentes como (límite en km, precio)."""
    return [
        (ZONA_1_KM, PRECIO_ZONA_1), (ZONA_2_KM, PRECIO_ZONA_2), (ZONA_3_KM, PRECIO_ZONA_3),
        (ZONA_4_KM, PRECIO_ZONA_4), (ZONA_5_KM, PRECIO_ZONA_5), (ZONA_6_KM, PRECIO_ZONA_6),
        (ZONA_7_KM, PRECIO_ZONA_7),
    ]

def zona_de(distance_km):
    """Número de zona (1-7) para una distancia, o None si pasa de la última."""
    for i, (limite, _) in enumerate(zonas(), start=1):
        if distance_km <= limite:
            return i
    return None

def num_es(valor, decimales=2):
    """Número con coma decimal y sin ceros sobrantes: 1.5 → "1,5", 60.0 → "60"."""
    texto = f"{valor:,.{decimales}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    if "," in texto:
        texto = texto.rstrip("0").rstrip(",")
    return texto

def euros(valor):
    return f"{valor:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")

def minutos(segundos):
    total = max(1, round(segundos / 60))
    h, m = divmod(total, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"

# Color fijo de cada zona, de la más cercana (verde) a la más lejana (rojo BigMat).
# Es el mismo en el mapa, en la ficha del porte y en el cuadro de zonas.
COLORES_ZONA = ["#1FA34A", "#00A9CE", "#2B7DE1", "#7B3FBF", "#FFB000", "#FF6A13", "#E4000F"]
COLOR_FUERA = "#14213D"

def color_zona(zona):
    return COLORES_ZONA[zona - 1] if zona else COLOR_FUERA

# Estilos dentro del iframe del mapa: las reglas de estilo.css no llegan ahí.
MAPA_ESTILO = """
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800&display=swap" rel="stylesheet">
<style>
  .leaflet-container { background: #F4F6FA; font-family: "Barlow Condensed", sans-serif; }
  /* Callejero apagado para que manden los colores de las zonas. */
  .leaflet-tile-pane { filter: grayscale(1) contrast(.7) brightness(1.16); }
  .cota-icon { background: none; border: 0; }
  .cota {
    display: inline-block; transform: translate(-50%, -50%); white-space: nowrap;
    font: 800 12px/1 "Barlow Condensed", sans-serif; letter-spacing: .04em; color: #fff;
    padding: 4px 8px 3px; border-radius: 999px; box-shadow: 0 1px 3px rgba(20,33,61,.3);
  }
  .cota.activa { font-size: 15px; padding: 5px 11px 4px; outline: 3px solid #FFD400; }
  .punto { display: flex; flex-direction: column; align-items: center; gap: 3px; transform: translate(-50%, -9px); white-space: nowrap; }
  .punto b {
    font: 800 12px/1 "Barlow Condensed", sans-serif; letter-spacing: .06em; text-transform: uppercase;
    color: #fff; background: #003C87; padding: 4px 7px 3px; border-radius: 4px;
  }
  .punto.destino b { background: #E4000F; }
  .leaflet-control-scale-line { border-color: #14213D; color: #14213D; background: rgba(255,255,255,.9); font: 700 11px "Barlow Condensed", sans-serif; }
  .leaflet-bar { border: 2px solid #003C87 !important; box-shadow: none !important; }
  .leaflet-bar a { color: #003C87; font-weight: 700; }
</style>
"""

SIMBOLO_ALMACEN = (
    '<svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">'
    '<circle cx="9" cy="9" r="7.5" fill="#fff" stroke="#003C87" stroke-width="3"/>'
    '<circle cx="9" cy="9" r="3" fill="#003C87"/></svg>'
)
SIMBOLO_DESTINO = (
    '<svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">'
    '<circle cx="9" cy="9" r="7.5" fill="#fff" stroke="#E4000F" stroke-width="3"/>'
    '<circle cx="9" cy="9" r="3" fill="#E4000F"/></svg>'
)

def lon_offset(lat, km):
    return km / (111.32 * math.cos(math.radians(lat)))

def plano_mapa(result=None):
    """Mapa del porte: un anillo de color por zona, la zona aplicada rellena y la ruta."""
    m = Map(location=[ORIGIN_LAT, ORIGIN_LON], zoom_start=12, control_scale=True)
    m.get_root().header.add_child(Element(MAPA_ESTILO))

    activa = zona_de(result["distancia_km"]) if result else None
    # Radio de la zona aplicada o, sin cálculo, de la zona 4; fuera de zonas,
    # el punto de la ruta más alejado del almacén.
    radio_vista = zonas()[(activa or 4) - 1][0]
    if result and not activa:
        radio_vista = max(
            math.hypot((lat - ORIGIN_LAT) * 110.574, (lon - ORIGIN_LON) * 111.32 * math.cos(math.radians(ORIGIN_LAT)))
            for lat, lon in result["coords"]
        )
    for i, (limite, precio) in enumerate(zonas(), start=1):
        es_activa = i == activa
        color = color_zona(i)
        # Solo la zona aplicada lleva relleno: en folium, pasar fill_color fuerza
        # el relleno aunque fill=False, así que solo se pasa en ese caso.
        relleno = {"fill": True, "fill_color": color, "fill_opacity": 0.14} if es_activa else {"fill": False}
        Circle(
            location=[ORIGIN_LAT, ORIGIN_LON], radius=limite * 1000,
            color=color, weight=6 if es_activa else 3, opacity=1 if es_activa else 0.85,
            interactive=False, **relleno,
        ).add_to(m)
        # Rótulos alternos a este y oeste para que no se pisen los anillos cercanos;
        # los anillos muy pequeños para el encuadre no se rotulan (están en el cuadro).
        if not es_activa and limite < radio_vista * 0.35:
            continue
        sentido = 1 if i % 2 else -1
        Marker(
            [ORIGIN_LAT, ORIGIN_LON + sentido * lon_offset(ORIGIN_LAT, limite)],
            icon=folium.DivIcon(
                html=(f'<span class="cota{" activa" if es_activa else ""}" style="background:{color}">'
                      f'Z{i} · {num_es(limite)} km · {precio} €</span>'),
                icon_size=(0, 0), class_name="cota-icon",
            ),
            interactive=False,
        ).add_to(m)

    if result:
        PolyLine(result["coords"], color="#FFFFFF", weight=10, opacity=0.95).add_to(m)
        PolyLine(result["coords"], color="#003C87", weight=5, opacity=1).add_to(m)
        Marker(
            [result["dest"][0], result["dest"][1]], tooltip=result["dest"][2],
            icon=folium.DivIcon(
                html=f'<div class="punto destino">{SIMBOLO_DESTINO}<b>Destino</b></div>',
                icon_size=(0, 0), class_name="cota-icon",
            ),
        ).add_to(m)

    Marker(
        [ORIGIN_LAT, ORIGIN_LON], tooltip="Almacén (origen de los portes)",
        icon=folium.DivIcon(
            html=f'<div class="punto">{SIMBOLO_ALMACEN}<b>Almacén</b></div>',
            icon_size=(0, 0), class_name="cota-icon",
        ),
    ).add_to(m)

    # Encuadre: la zona aplicada y la siguiente, para ver el salto de precio. Se
    # calcula el zoom en lugar de usar fit_bounds porque Leaflet encuadra mal si el
    # iframe aún no tiene su tamaño definitivo (pasaba al volver a pintar la página).
    radio_encuadre = radio_vista
    if activa and activa < len(zonas()):
        radio_encuadre = min(zonas()[activa][0], radio_vista * 1.6)
    metros_por_px_z0 = 156543.03 * math.cos(math.radians(ORIGIN_LAT))
    zoom = math.log2(metros_por_px_z0 * 560 / (radio_encuadre * 2000 * 1.08))
    zoom = max(8, min(16, math.floor(zoom * 4) / 4))
    mapa = m.get_name()
    # Se reencuadra solo al cargar; al redimensionar se recalcula el tamaño sin
    # deshacer el zoom que haya elegido quien lo está mirando.
    m.get_root().script.add_child(Element(
        f"function encuadrar() {{ {mapa}.invalidateSize(); {mapa}.setView([{ORIGIN_LAT}, {ORIGIN_LON}], {zoom}); }}"
        f"setTimeout(encuadrar, 150); setTimeout(encuadrar, 700);"
        f"window.addEventListener('resize', function () {{ {mapa}.invalidateSize(); }});"
    ))
    m.options["zoom"] = zoom
    m.options["zoomSnap"] = 0.25

    st_folium(m, height=640, use_container_width=True, returned_objects=[], key="plano-mapa")

def madrid_now_iso():
    if ZoneInfo is not None:
        tz = ZoneInfo("Europe/Madrid")
        return datetime.now(tz).isoformat(timespec="seconds")
    return datetime.now().isoformat(timespec="seconds")

# =========================================================
# Logging automático a Google Sheets
# =========================================================
# Pestaña "portes": solo lo esencial para el día a día, con títulos legibles.
# La pestaña "logs" sigue guardando todos los datos (FIELDNAMES).
PORTES_COLUMNAS = [
    ("Fecha porte", "fecha_porte"),
    ("Sección", "seccion"),
    ("Albarán", "albaran"),
    ("Cliente", "cliente_nombre"),
    ("Teléfono", "cliente_telefono"),
    ("Dirección", "dest_geocoded_title"),
    ("Km", "distance_km"),
    ("Precio (€)", "price_eur"),
    ("Operario", "operario_nombre"),
    ("Anotaciones", "anotaciones"),
    ("Registrado", "timestamp_iso"),
]

def append_to_gsheet(sh, worksheet_name: str, header: list, values: list):
    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=1, cols=len(header))
        ws.append_row(header, value_input_option="RAW")
    current = ws.row_values(1)
    if not current:
        ws.append_row(header, value_input_option="RAW")
    elif len(current) < len(header) and current == header[:len(current)]:
        # Hoja creada antes de añadir columnas nuevas: se amplía la cabecera.
        if ws.col_count < len(header):
            ws.add_cols(len(header) - ws.col_count)
        ws.update(values=[header], range_name="A1", value_input_option="RAW")
    ws.append_row(values, value_input_option="USER_ENTERED")

def log_to_sheets(row: dict):
    """Guarda el porte en "logs" (completo) y en "portes" (resumen).

    Devuelve (guardado, mensaje). Si "logs" se guarda pero "portes" falla,
    devuelve guardado=True con un aviso, para no duplicar la fila al reintentar.
    """
    logs_sheet_id = st.secrets.get("LOGS_SHEET_ID", "")
    if not logs_sheet_id:
        return False, "Falta 'LOGS_SHEET_ID' en Secrets."
    if not _gspread_ready:
        return False, "Faltan dependencias gspread/google-auth."
    try:
        sh = sheets_client_from_secrets().open_by_key(logs_sheet_id)
        append_to_gsheet(sh, "logs", FIELDNAMES, [row.get(k, "") for k in FIELDNAMES])
    except Exception as e:
        return False, str(e)
    try:
        append_to_gsheet(
            sh, "portes",
            [titulo for titulo, _ in PORTES_COLUMNAS],
            [row.get(k, "") for _, k in PORTES_COLUMNAS],
        )
    except Exception as e:
        return True, f"Guardado en 'logs', pero no en la pestaña 'portes': {e}"
    return True, None

# =========================================================
# INTERFAZ
# =========================================================
CARPETA = Path(__file__).parent
st.markdown(f"<style>{(CARPETA / 'estilo.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
LOGO = base64.b64encode((CARPETA / "assets" / "bigmat-rodriguez.png").read_bytes()).decode()

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

def fecha_larga(d):
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"

def esc(texto):
    return html.escape(str(texto))

def rotulo_seccion(numero, texto):
    st.markdown(
        f'<div class="seccion-hoja{" primera" if numero == 1 else ""}"><span class="num">{numero}</span>{texto}</div>',
        unsafe_allow_html=True,
    )

def burbuja_html(precio):
    enteros, decimales = euros(precio).split(",")
    return (f'<div class="burbuja"><div class="euros">{enteros}<sup>,{decimales} €</sup></div>'
            f'<div class="pie">Precio del porte</div></div>')

def chip_zona_html(zona):
    if zona:
        return (f'<span class="chip-zona" style="background:{color_zona(zona)}">'
                f'<b style="color:{color_zona(zona)}">Z{zona}</b>Zona {zona}</span>')
    return (f'<span class="chip-zona" style="background:{COLOR_FUERA}">'
            f'<b style="color:{COLOR_FUERA}">+</b>Más de {num_es(ZONA_7_KM)} km</span>')

def ficha_vacia_html():
    return """
<div class="ficha vacia">
  <div class="franja"><span class="que">Nuevo porte</span><span class="alb">Sin calcular</span></div>
  <div class="oferta">
    <div class="burbuja"><div class="euros">— €</div><div class="pie">Precio del porte</div></div>
    <div class="pie-ficha">
      Rellena la hoja de pedido de la izquierda y pulsa <strong>Calcular ruta y precio</strong>.
      Aquí aparecerán el precio, la zona y los datos del porte para revisarlos antes de guardarlos.
    </div>
  </div>
</div>"""

def ficha_html(r):
    activa = zona_de(r["distancia_km"])
    exp = r["seccion"].startswith("Exposición")
    tag = f'<span class="seccion-tag {"exp" if exp else "alm"}">{"EXP" if exp else "ALM"}</span>'
    albaran = esc(r["albaran"]) if r["albaran"] else "Sin albarán"
    if r["saved"]:
        hora = r.get("saved_at", "")
        pegatina = (f'<div class="pegatina registrado">Registrado'
                    f'<small>{esc(hora)} · {esc(r["operario_nombre"])}</small></div>')
    else:
        pegatina = '<div class="pegatina pendiente">Pendiente<small>de guardar</small></div>'
    nota = ""
    if r["anotaciones"]:
        nota = f'<div class="nota"><span class="etq">Anotaciones</span><span>{esc(r["anotaciones"])}</span></div>'
    operario = esc(r["operario_nombre"])
    if r["operario_nombre"] != r["operario_codigo"]:
        operario += f' <span class="suave">· cód. {esc(r["operario_codigo"])}</span>'
    return f"""
<div class="ficha">
  {pegatina}
  <div class="franja"><span class="que">Porte</span><span class="alb"><small>Albarán</small>{albaran}</span></div>
  <div class="oferta">
    {burbuja_html(r["price"])}
    <div class="datos-zona">
      {chip_zona_html(activa)}
      <div class="km">{num_es(r["distancia_km"])}<small>km</small></div>
      <div class="tiempo">en camión desde el almacén · {minutos(r["duration_s"])}</div>
    </div>
  </div>
  {nota}
  <dl>
    <dt>Sección</dt><dd>{tag}{esc(r["seccion"])}</dd>
    <dt>Fecha</dt><dd>{fecha_larga(r["fecha_porte"]).capitalize()}</dd>
    <dt>Cliente</dt><dd>{esc(r["cliente_nombre"])}</dd>
    <dt>Teléfono</dt><dd>{esc(r["cliente_telefono"])}</dd>
    <dt>Operario</dt><dd>{operario}</dd>
    <dt>Destino</dt><dd>{esc(r["dest"][2])}</dd>
  </dl>
</div>"""

def cuadro_zonas_html(activa=None, fuera=False):
    filas = []
    desde = 0
    for i, (limite, precio) in enumerate(zonas(), start=1):
        clase = ' class="activa"' if i == activa else ""
        filas.append(
            f'<tr{clase}><td><span class="z" style="background:{color_zona(i)}">Z{i}</span></td>'
            f'<td>{num_es(desde)} – {num_es(limite)} km</td><td class="n precio">{precio} €</td></tr>'
        )
        desde = limite
    clase = ' class="activa"' if fuera else ""
    filas.append(
        f'<tr{clase}><td><span class="z" style="background:{COLOR_FUERA}">+Z7</span></td>'
        f'<td>Más de {num_es(ZONA_7_KM)} km</td>'
        f'<td class="n precio">{PRECIO_ZONA_7} € +{num_es(PRECIO_POR_KM_EXTRA)} €/km</td></tr>'
    )
    if REMOTE_CFG:
        fuente = "Tarifas de la hoja de control. Para cambiarlas, edita esa hoja, no la app."
    else:
        fuente = "No se pudo leer la hoja de control: se usan las tarifas por defecto del código."
    return f"""
<div class="cuadro">
  <table>
    <caption>Tarifas por zona</caption>
    <thead><tr><th>Zona</th><th>Distancia</th><th class="n">Precio</th></tr></thead>
    <tbody>{"".join(filas)}</tbody>
  </table>
  <div class="fuente">{fuente}</div>
</div>"""

LEYENDA_HTML = """
<div class="leyenda">
  <span><i class="l-zonas"></i>Zonas 1 a 7</span>
  <span><i class="l-ruta"></i>Ruta del camión</span>
  <span><i class="l-almacen"></i>Almacén</span>
  <span><i class="l-destino"></i>Destino</span>
</div>"""

api_key = get_api_key()
logs_ok = bool(st.secrets.get("LOGS_SHEET_ID", ""))

with st.sidebar:
    rotulo_seccion(1, "Datos del porte")
    seccion = st.radio("Sección", SECCIONES, index=None)
    albaran = st.text_input(
        "Número de albarán (opcional)", value="",
        placeholder="A01/T01… almacén · A02/T02… exposición",
    )
    fecha_porte = st.date_input("Fecha del porte", value=None, format="DD/MM/YYYY")
    operario_codigo = st.text_input("Código de operario", value="")
    operario_nombre = OPERARIOS.get(normalize_operario(operario_codigo), "")
    if operario_nombre:
        st.markdown(f'<p class="operario-ok">{esc(operario_nombre)}</p>', unsafe_allow_html=True)
    elif operario_codigo.strip() and OPERARIOS:
        st.markdown('<p class="operario-ko">Código de operario no encontrado</p>', unsafe_allow_html=True)

    rotulo_seccion(2, "Cliente")
    cliente_nombre = st.text_input("Nombre del cliente", value="")
    cliente_telefono = st.text_input("Teléfono del cliente", value="")

    rotulo_seccion(3, "Destino")
    dest_address = st.text_input("Dirección destino", value="")
    dest_postal = st.text_input("Código postal (opcional)", value="")
    dest_city = st.text_input("Población (opcional)", value="Madrid")
    anotaciones = st.text_area(
        "Anotaciones (opcional)", value="",
        placeholder="Ej.: solo se puede entrar hasta las 12:00",
    )

    go = st.button("Calcular ruta y precio", type="primary", use_container_width=True)
    aviso = st.empty()

    notas = ["Los portes se calculan siempre desde el almacén, en ruta de camión."]
    if not logs_ok:
        notas.append("Registro en Sheets desactivado: falta 'LOGS_SHEET_ID' en Secrets.")
    st.markdown(
        '<div class="notas-conexion">' + "".join(f"<p>{n}</p>" for n in notas) + "</div>",
        unsafe_allow_html=True,
    )
    if REMOTE_CONTROL_ID:
        with st.expander("Configuración remota (debug)"):
            st.write("CONTROL_SHEET_ID:", REMOTE_CONTROL_ID)
            st.json(REMOTE_CFG)

def validar():
    """Devuelve el primer error de la hoja de datos, o None si está completa."""
    if not api_key:
        return "Falta HERE_API_KEY. Añádelo en la sección de secretos o como variable de entorno."
    if not seccion:
        return "Selecciona la sección (Exposición Vital Aza o Almacén Ezequiel Solana) antes de calcular."
    prefijos = ALBARAN_PREFIJOS[seccion]
    alb = albaran.strip().upper()
    if alb and not any(alb.startswith(p) and len(alb) > len(p) for p in prefijos):
        return (
            f"El número de albarán de {seccion} debe empezar por {' o '.join(prefijos)} "
            f"(por ejemplo, {prefijos[0]}1234)."
        )
    if not fecha_porte:
        return "Indica la fecha en la que se va a realizar el porte antes de calcular."
    if not operario_codigo.strip():
        return "Introduce el código de operario antes de calcular."
    if OPERARIOS and not operario_nombre:
        return "El código de operario no está en la pestaña 'operarios' de la hoja de control."
    if not cliente_nombre.strip():
        return "Introduce el nombre del cliente antes de calcular."
    if not cliente_telefono.strip():
        return "Introduce el teléfono del cliente antes de calcular."
    if not dest_address.strip():
        return "Introduce la dirección de destino antes de calcular."
    return None

def calcular():
    """Calcula ruta y precio y deja el porte pendiente de guardar. Devuelve un error o None."""
    global operario_nombre
    alb = albaran.strip().upper()
    if not OPERARIOS:
        # Sin lista de operarios no se puede traducir: se guarda el código.
        operario_nombre = operario_codigo.strip()

    with st.spinner("Buscando la dirección de destino…"):
        try:
            dlat, dlon, dtitle, dacc_lat, dacc_lon = geocode_address(
                dest_address, api_key, postal_code=dest_postal or None, city=dest_city or None
            )
            dest = (dacc_lat, dacc_lon, dtitle)
        except Exception as e:
            return f"No se encontró la dirección de destino: {e}"

    with st.spinner("Calculando la ruta del camión…"):
        try:
            coords, length_m, duration_s = truck_route(
                (ORIGIN_LAT, ORIGIN_LON), (dest[0], dest[1]), api_key
            )
        except Exception as e:
            return f"No se pudo calcular la ruta del camión: {e}"

    distancia_km = round(length_m / 1000.0, 2)
    dur = human_duration(duration_s)
    price = compute_tariff(distancia_km)

    row = {
        "timestamp_iso": madrid_now_iso(),
        "cliente_nombre": cliente_nombre.strip(),
        "operario_codigo": operario_codigo.strip(),
        "operario_nombre": operario_nombre,
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
        "seccion": seccion,
        "fecha_porte": fecha_porte.isoformat(),
        "anotaciones": anotaciones.strip(),
        "zona_5_km": ZONA_5_KM, "zona_6_km": ZONA_6_KM, "zona_7_km": ZONA_7_KM,
        "precio_z5": PRECIO_ZONA_5, "precio_z6": PRECIO_ZONA_6, "precio_z7": PRECIO_ZONA_7,
        # El apóstrofo hace que Sheets lo guarde como texto y no se pierdan
        # el "+" del prefijo ni los ceros iniciales.
        "cliente_telefono": f"'{cliente_telefono.strip()}",
        "albaran": alb,
    }

    # No se registra aquí: el "row" espera a que el usuario confirme con el botón.
    st.session_state["result"] = {
        "seccion": seccion,
        "albaran": alb,
        "fecha_porte": fecha_porte,
        "anotaciones": anotaciones.strip(),
        "cliente_nombre": cliente_nombre.strip(),
        "cliente_telefono": cliente_telefono.strip(),
        "operario_codigo": operario_codigo.strip(),
        "operario_nombre": operario_nombre,
        "dest": dest,
        "coords": coords,
        "distancia_km": distancia_km,
        "duration_s": int(duration_s),
        "dur": dur,
        "price": price,
        "row": row,
        "saved": False,
        "log_ok": None,
        "log_err": None,
    }
    return None

if go:
    # Un cálculo nuevo descarta el anterior, para no confundir datos viejos con los nuevos.
    st.session_state["result"] = None
    error = validar() or calcular()
    if error:
        aviso.error(error)

result = st.session_state.get("result")

HOY = datetime.now(ZoneInfo("Europe/Madrid")) if ZoneInfo else datetime.now()
st.markdown(
    f"""
<div class="folleto-cabecera">
  <div class="placa"><img src="data:image/png;base64,{LOGO}" alt="BigMat Rodríguez"></div>
  <div class="titulo">
    <h1>Portes a obra y domicilio</h1>
    <div class="sub"><span>Cálculo y registro de portes en camión</span></div>
  </div>
  <div class="hoy"><span class="dia">{DIAS[HOY.weekday()]}</span><span class="fecha">{HOY:%d/%m/%Y}</span></div>
</div>""",
    unsafe_allow_html=True,
)
if not api_key:
    st.error("Configura tu HERE_API_KEY en **st.secrets** o en la variable de entorno HERE_API_KEY.")

col_plano, col_cajetin = st.columns([1.85, 1], gap="large")

with col_plano:
    with st.container(key="plano"):
        plano_mapa(result)
        st.markdown(LEYENDA_HTML, unsafe_allow_html=True)

with col_cajetin:
    if result:
        st.markdown(ficha_html(result), unsafe_allow_html=True)
        if result["saved"]:
            if result["log_err"]:
                st.warning(result["log_err"])
        elif not logs_ok:
            st.button("Confirmar y guardar porte", type="primary", use_container_width=True, disabled=True)
            st.info(
                "No se puede guardar: la app no tiene configurada la hoja de portes (falta 'LOGS_SHEET_ID'). "
                "Avisa a quien mantiene la app."
            )
        else:
            if st.button("Confirmar y guardar porte", type="primary", use_container_width=True):
                with st.spinner("Guardando en la hoja de portes…"):
                    log_ok, log_err = log_to_sheets(result["row"])
                result["log_ok"] = log_ok
                result["log_err"] = log_err
                result["saved"] = log_ok
                if log_ok:
                    ahora = datetime.now(ZoneInfo("Europe/Madrid")) if ZoneInfo else datetime.now()
                    result["saved_at"] = f"{ahora:%d/%m %H:%M}"
                st.session_state["result"] = result
                st.rerun()
            if result["log_ok"] is False and result["log_err"]:
                st.error(
                    f"No se pudo guardar en la hoja: {result['log_err'].rstrip('.')}. "
                    "Vuelve a intentarlo; si se repite, avisa a quien mantiene la app."
                )
        activa = zona_de(result["distancia_km"])
        st.markdown(cuadro_zonas_html(activa, fuera=activa is None), unsafe_allow_html=True)
    else:
        st.markdown(ficha_vacia_html(), unsafe_allow_html=True)
        st.markdown(cuadro_zonas_html(), unsafe_allow_html=True)
