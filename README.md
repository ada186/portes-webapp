# Cálculo de porte por ruta (HERE) — Streamlit (CSV + Google Sheets)

## Google Sheets (Service Account)
- Añade en **Streamlit Secrets** una clave con nombre `gcp_service_account` que contenga **el JSON completo** del Service Account.
- Comparte tu Google Sheet con el `client_email` del SA (editor).
- Usa el **Spreadsheet ID** (lo que va entre `/d/` y `/edit`).

En la barra lateral: activa "Subir a Google Sheets", pega el Spreadsheet key y el nombre de la hoja.

## Dependencias
`pip install -r requirements.txt`

## Ejecutar
`streamlit run app.py`
