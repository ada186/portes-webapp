# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Personal de oficina y logística de una tienda de materiales de construcción y reformas en Madrid. Desde un ordenador, organizan los portes en camión del día y los registran; normalmente sin el cliente delante.

## Product Purpose
Calcular el precio de un porte en camión desde el almacén hasta la obra o el domicilio del cliente: ruta real de camión (HERE), distancia, zona tarifaria y precio. Después, registrar el porte confirmado en Google Sheets para planificar el reparto. El éxito es que cada porte tenga el precio correcto y quede registrado completo, con sección, albarán, fecha, cliente, teléfono, operario y anotaciones, sin errores ni duplicados.

## Positioning
Herramienta interna hecha a medida para dos sedes concretas, no un producto comercial. Calcula la tarifa por zonas sobre la ruta real que puede hacer un camión de 16 t, 4 m de alto y 10 m de largo, no en línea recta. Las tarifas y la plantilla de operarios se controlan desde una hoja de cálculo, sin tocar código.

## Operating Context
- Dos secciones originan pedidos: Exposición Vital Aza (albaranes A02/T02) y Almacén Ezequiel Solana (albaranes A01/T01). Los portes salen de un origen fijo en el almacén.
- Siete zonas concéntricas por km, con precio fijo cada una y €/km extra a partir de la última. Valores en la hoja de control (pestaña `config`).
- Operarios identificados por código; el nombre se resuelve con la pestaña `operarios` de la hoja de control.
- Registro en el Google Sheets `portes_logs`: pestaña `portes` (resumen diario) y pestaña `logs` (todos los datos).
- Las anotaciones recogen restricciones de acceso a la obra o al domicilio, por ejemplo "solo se puede entrar hasta las 12:00".

## Capabilities and Constraints
- Streamlit (Python) desplegado desde la rama `main` de un repositorio público de GitHub. El diseño se limita al tema de Streamlit, al CSS inyectado, a la composición con columnas y barra lateral, y al mapa folium.
- El flujo es: rellenar datos → calcular → revisar → confirmar y guardar. Guardar es un paso explícito.
- Campos obligatorios: sección, fecha del porte, nombre y teléfono del cliente, código de operario y dirección de destino. Opcionales: albarán y anotaciones.
- Sin datos personales (nombres de empleados, claves) en el repositorio.

## Brand Commitments
La tienda es BigMat Rodríguez y la app debe llevar su logo (confirmado por el usuario): `assets/bigmat-rodriguez.png`, el rótulo «BigMat / RODRIGUEZ» recortado de los carteles de la tienda, copiado sin cambios del proyecto `contenedores-webapp`. No redibujarlo ni recrearlo. Colores de marca en uso: azul BigMat #003C87 y rojo BigMat #E4000F. El usuario pidió una app colorida.

## Evidence on Hand
Logo BigMat Rodríguez en `assets/bigmat-rodriguez.png` (origen: carteles de la tienda, vía `contenedores-webapp`). No inventar datos de clientes.

## Product Principles
1. El precio y la zona se leen de un vistazo, sin dudas.
2. Lo que se guarda en la hoja es exactamente lo que se ve antes de confirmar.
3. La sección (exposición o almacén) se identifica en todo momento, sin separar los portes en dos herramientas.
4. Rapidez para un uso repetido cada día en oficina: pocos clics, errores claros y en el sitio.
