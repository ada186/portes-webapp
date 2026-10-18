---
name: Portes · BigMat Rodríguez
description: Cálculo y registro de portes en camión, presentado como una oferta del folleto BigMat.
colors:
  rojo: "#E4000F"
  rojo-hondo: "#B0000B"
  amarillo: "#FFD400"
  azul: "#003C87"
  hoja-campo: "#0B4FA3"
  verde-registrado: "#157A36"
  zona-1: "#1FA34A"
  zona-2: "#00A9CE"
  zona-3: "#1F6ED4"
  zona-4: "#7B3FBF"
  zona-5: "#FFB000"
  zona-6: "#FF6A13"
  zona-7: "#E4000F"
  tinta: "#14213D"
  tinta-suave: "#4A5671"
  blanco: "#FFFFFF"
  gris: "#F4F6FA"
  linea: "#D7DDE8"
  borde-campo: "#C9D1DE"
  hoja-rotulo: "#CFE0F7"
  hoja-borde: "#5C86C4"
typography:
  display:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "2.7rem"
    fontWeight: 800
    lineHeight: 0.92
    letterSpacing: "-0.01em"
  precio:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "3.6rem"
    fontWeight: 800
    lineHeight: 0.85
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "1.35rem"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "0.01em"
  cifra:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "2.1rem"
    fontWeight: 800
    lineHeight: 1
    fontFeature: "tnum"
  body:
    fontFamily: "Barlow, sans-serif"
    fontSize: "0.96rem"
    fontWeight: 400
    lineHeight: 1.35
  label:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 700
    letterSpacing: "0.07em"
  boton:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 800
    letterSpacing: "0.03em"
rounded:
  etiqueta: "0.25rem"
  pegatina: "0.3rem"
  campo: "0.4rem"
  bloque: "0.6rem"
  pildora: "999px"
  circulo: "50%"
spacing:
  celda: "0.45rem"
  bloque: "1rem"
  separacion: "1.2rem"
components:
  button-primary:
    backgroundColor: "{colors.rojo}"
    textColor: "{colors.blanco}"
    typography: "{typography.boton}"
    rounded: "{rounded.campo}"
    height: "3rem"
  button-primary-hover:
    backgroundColor: "{colors.rojo-hondo}"
    textColor: "{colors.blanco}"
  boton-abrir-hoja:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.amarillo}"
    rounded: "{rounded.campo}"
    size: "2.75rem"
  campo-hoja:
    backgroundColor: "{colors.hoja-campo}"
    textColor: "{colors.blanco}"
    rounded: "{rounded.campo}"
  franja-ficha:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.blanco}"
    typography: "{typography.headline}"
    padding: "0.55rem 1rem 0.5rem"
  burbuja-precio:
    backgroundColor: "{colors.amarillo}"
    textColor: "{colors.rojo}"
    typography: "{typography.precio}"
    rounded: "{rounded.circulo}"
    size: "9.6rem"
  chip-zona:
    rounded: "{rounded.pildora}"
    padding: "0.25rem 0.85rem 0.22rem 0.3rem"
  pegatina-pendiente:
    backgroundColor: "{colors.amarillo}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.pegatina}"
    padding: "0.4rem 0.75rem 0.38rem"
  pegatina-registrado:
    backgroundColor: "{colors.verde-registrado}"
    textColor: "{colors.blanco}"
    rounded: "{rounded.pegatina}"
    padding: "0.4rem 0.75rem 0.38rem"
  nota-ficha:
    backgroundColor: "{colors.amarillo}"
    textColor: "{colors.tinta}"
    padding: "0.6rem 1rem"
  fila-tarifa-activa:
    backgroundColor: "{colors.amarillo}"
    textColor: "{colors.tinta}"
---

# Design System: Portes · BigMat Rodríguez

## Overview

**Creative North Star: "Folleto de ofertas BigMat"**

Cada porte se presenta como una oferta del folleto de la tienda: el precio va en una burbuja amarilla con borde rojo, la información se organiza en bloques planos de rojo, amarillo y azul BigMat sobre blanco, y cada zona tarifaria tiene su color propio, que se repite igual en el mapa, en la ficha y en el cuadro de tarifas. Es una herramienta de oficina de uso diario, pero no tiene el aspecto gris de una herramienta de oficina: habla el idioma visual de los carteles y folletos que el personal ya ve en la tienda.

La densidad es la de un folleto de trabajo: una barra lateral azul que funciona como hoja de pedido numerada, una cabecera roja con la placa blanca del logo, un mapa grande y una ficha que se lee de un vistazo (precio, zona por su color, km). Los titulares son Barlow Condensed negra, cursiva y en mayúsculas; los datos van en Barlow normal y legible. Solo los recursos propios del folleto se inclinan (la burbuja, la pegatina y la cinta del subtítulo); los datos nunca.

Se rechazan expresamente la herramienta gris de oficina y el panel de métricas neutro.

**Key Characteristics:**
- Bloques planos de rojo, amarillo y azul BigMat sobre blanco, sin degradados decorativos.
- Siete colores de zona fijos, de verde (cerca) a rojo (lejos), cada uno con su tinta de texto fija.
- Titulares, precios y botones en Barlow Condensed 800 cursiva en mayúsculas; datos en Barlow.
- Precio en burbuja girada; estado del porte en una pegatina que cambia de amarilla a verde al registrar.
- Esquinas suaves (0,4–0,6rem) y sombras difusas teñidas, nunca sombras duras.

## Colors

Tres colores de marca a bloques sobre blanco, una escala fija de siete colores de zona y neutros azulados derivados de la tinta.

### Primary
- **Rojo BigMat** (rojo): cabecera de folleto, botón principal, borde de la burbuja y cifra del precio, punto de destino, etiqueta EXP de exposición. Es el color de la acción y del precio.
- **Rojo hondo** (rojo-hondo): estado hover del botón principal y texto de los avisos de error de la hoja de pedido (sobre blanco, 7,4:1).

### Secondary
- **Azul BigMat** (azul): fondo de la hoja de pedido (barra lateral), bloque de la fecha en la cabecera, franja de la ficha, cabecera del cuadro de tarifas, bordes de 2px de los bloques del área principal, ruta del camión, almacén, etiqueta ALM y anillo de foco del área principal.
- **Azul campo** (hoja-campo): fondo de los campos de la hoja de pedido sobre el azul BigMat.

### Tertiary
- **Amarillo folleto** (amarillo): lo que pide atención ahora. Burbuja del precio, cinta del subtítulo, pegatina «Pendiente de guardar», franja de anotaciones, fila aplicada del cuadro, rótulo de la zona aplicada en el mapa (contorno de 3px), números de sección de la hoja, nombre de operario reconocido, selección de texto y anillo de foco en la barra lateral.
- **Verde registrado** (verde-registrado): solo la pegatina «Registrado» (texto blanco, 5,4:1).

### Colores de zona
- **Zona 1 a zona 7** (zona-1 … zona-7): verde, cian, azul, violeta, ámbar, naranja y rojo, de la zona más cercana a la más lejana. Se usan en los anillos del mapa, en los rótulos del mapa, en el chip de zona de la ficha y en las píldoras del cuadro. La tinta del texto sobre cada color es fija: tinta oscura sobre zonas 1, 2, 5 y 6; blanco sobre zonas 3, 4 y 7. Fuera de zonas se usa la tinta oscura con texto blanco.

### Neutral
- **Tinta** (tinta): texto principal, cifras de km y precios del cuadro, texto sobre amarillo.
- **Tinta suave** (tinta-suave): texto secundario, tiempo de viaje, leyenda del mapa, cabeceras de columna y notas de pie.
- **Blanco** (blanco): fondo de página y de los bloques; texto sobre rojo, azul y verde.
- **Gris folleto** (gris): fondo de la zona de oferta de la ficha, del pie del cuadro y del lienzo del mapa.
- **Línea** (linea): divisores de 1px entre filas de la ficha y del cuadro.
- **Borde de campo** (borde-campo): borde de los campos de Streamlit en el área principal.
- **Rótulo de hoja** (hoja-rotulo): etiquetas de campo y notas sobre la barra lateral azul (7,8:1).
- **Borde de hoja** (hoja-borde): borde de los campos de la barra lateral.

### Named Rules
**The Color de Zona Rule.** Cada zona tiene un único color y una única tinta, definidos una sola vez en el código (COLORES_ZONA y TINTAS_ZONA) y reutilizados en el mapa, la ficha y el cuadro. Nunca se elige la tinta a mano ni se cambia el color de una zona en una sola vista.

**The Amarillo de Atención Rule.** El amarillo marca lo que hay que mirar ahora: el precio, lo pendiente, lo aplicado, las anotaciones y el foco en la hoja. No se usa como decoración de fondo.

**The Bloque Plano Rule.** Rojo, amarillo y azul se aplican como bloques planos y enteros. El único degradado es la tira de la leyenda, que es la propia escala de zonas en pequeño.

## Typography

**Display Font:** Barlow Condensed (con sans-serif)
**Body Font:** Barlow (con sans-serif)

**Character:** La condensada negra en cursiva y mayúsculas es la voz del folleto (titulares, precios, botones); Barlow normal deja los datos del porte tranquilos y legibles. Las cifras usan números tabulares.

### Hierarchy
- **Display** (800 cursiva, 2,7rem; 2,2rem en móvil, interlineado 0,92, mayúsculas): titular de la cabecera de folleto.
- **Precio** (800 cursiva, 3,6rem, interlineado 0,85): cifra del precio dentro de la burbuja; los céntimos y el € en superíndice al 42 %.
- **Headline** (800 cursiva, 1,15–1,35rem, mayúsculas): franja de la ficha, cabecera del cuadro y títulos numerados de la hoja de pedido (1,2rem).
- **Cifra** (800, 2,1rem, interlineado 1): km de la ficha, con la unidad al 50 % en tinta suave.
- **Body** (400, 0,9–0,96rem, interlineado 1,35–1,4; base de Streamlit 15px): datos de la ficha, filas del cuadro y notas.
- **Label** (700, 0,78–0,84rem, espaciado 0,05–0,08em, mayúsculas): etiquetas de campo, términos de la ficha (en azul), cabeceras de columna, leyenda del mapa y pie de la burbuja.
- **Botón** (800 cursiva, 1,2rem, espaciado 0,03em, mayúsculas): botones principales.

### Named Rules
**The Voz de Folleto Rule.** Barlow Condensed 800 cursiva en mayúsculas solo para lo que se anuncia (titulares, precios, botones, estados); los datos que hay que leer y copiar van en Barlow normal, sin cursiva.

## Layout

Página ancha de hasta 1440px. La barra lateral de Streamlit es la hoja de pedido azul, dividida en tres secciones numeradas (1 Datos del porte, 2 Cliente, 3 Destino) con el botón rojo Calcular al final y los avisos de validación bajo el campo que falla. En el área principal, la cabecera de folleto ocupa todo el ancho (separación inferior 1,2rem) en una rejilla de tres columnas: placa del logo, titular y bloque de fecha. Debajo, dos columnas en proporción 1,85 : 1 con separación amplia: el mapa (640px de alto, con la leyenda dentro del mismo bloque) y la columna de la ficha con el cuadro de tarifas debajo (1rem de separación).

El ritmo interno es de 1rem de relleno horizontal en bloques y filas, y 0,45rem vertical en las celdas de la ficha. Por debajo de 720px la cabecera se apila en una columna, la placa pierde el corte inclinado, la oferta de la ficha se centra en una columna y la pegatina deja de flotar y se coloca en línea, sin giro. Con la barra lateral plegada, se abre con un botón azul con icono amarillo de 2,75rem.

## Elevation & Depth

Sistema plano con elevación ligera: los bloques se separan por color y por bordes azules de 2px, y solo unas pocas piezas proyectan sombra. Las sombras son siempre difusas y teñidas del color del bloque o de la tinta.

### Shadow Vocabulary
- **Cabecera** (`box-shadow: 0 2px 4px rgba(20, 33, 61, 0.12), 0 10px 26px rgba(228, 0, 15, 0.18)`): sombra roja suave bajo la cabecera de folleto.
- **Ficha** (`box-shadow: 0 2px 4px rgba(20, 33, 61, 0.08), 0 12px 28px rgba(0, 60, 135, 0.12)`): sombra azul bajo la ficha del porte.
- **Burbuja** (`box-shadow: 0 3px 6px rgba(20, 33, 61, 0.18)`): despega la burbuja del precio.
- **Pegatina** (`box-shadow: 0 2px 5px rgba(20, 33, 61, 0.22)`): la pegatina de estado parece pegada encima de la ficha.
- **Botón principal** (`box-shadow: 0 2px 6px rgba(176, 0, 11, 0.35)`): se quita cuando el botón está desactivado.
- **Botón de abrir hoja** (`box-shadow: 0 2px 6px rgba(0, 60, 135, 0.3)`).
- **Rótulo de mapa** (`box-shadow: 0 1px 3px rgba(20,33,61,.3)`): píldoras de zona sobre el mapa.

### Named Rules
**The Sombra Difusa Rule.** Toda sombra tiene desenfoque y va teñida; nunca sombras duras desplazadas sin desenfoque. El cuadro de tarifas y el bloque del mapa no llevan sombra: se separan solo por su borde azul.

## Shapes

Esquinas suaves: 0,6rem en los bloques grandes (cabecera, mapa, ficha, cuadro), 0,4rem en campos y botones, 0,3rem en la pegatina y 0,25rem en las etiquetas EXP/ALM. Las píldoras (999px) se usan para el chip de zona, las zonas del cuadro y los rótulos del mapa; los círculos para la burbuja del precio, el número de zona del chip, los números de sección de la hoja y los puntos de almacén y destino (anillo de color con centro blanco y punto). Los bloques del área principal llevan borde azul de 2px. La placa del logo tiene el borde derecho cortado en diagonal (22px) en escritorio.

Los únicos elementos inclinados son los del folleto: la burbuja girada -7°, la pegatina girada 4° y la cinta amarilla del subtítulo con sesgo de -8° (el texto se endereza dentro).

## Components

### Buttons
Rojos, grandes y con voz de folleto.
- **Shape:** esquinas suaves (0,4rem), alto mínimo de 3rem, ancho completo de su columna.
- **Primary:** fondo rojo BigMat, texto blanco en Barlow Condensed 800 cursiva mayúsculas a 1,2rem, sombra roja difusa.
- **Hover / Focus:** hover a rojo hondo (150ms ease-out); al pulsar baja 1px (120ms). Foco con anillo azul de 3px y separación de 2px en el área principal, amarillo en la barra lateral.
- **Disabled:** sin sombra, con el aspecto desactivado de Streamlit.
- **Abrir hoja de pedido:** cuadrado azul de 2,75rem con el icono en amarillo a 1,5rem.

### Chips
- **Chip de zona:** píldora con el color de la zona y su tinta fija, Barlow Condensed 800 a 1,15rem; empieza con un círculo blanco de 2,1rem con «Z1…Z7» en tinta. Fuera de zonas, fondo tinta con «+».
- **Zona en el cuadro:** píldora pequeña (0,85rem, mínimo 2,4rem) con el mismo color y tinta.
- **Etiqueta de sección:** EXP en rojo, ALM en azul, texto blanco, 0,8rem 800.

### Cards / Containers
- **Ficha del porte:** fondo blanco, borde azul de 2px, esquinas de 0,6rem, sombra de ficha. Franja azul superior (qué y albarán), zona de oferta en gris con la burbuja a la izquierda y chip, km y tiempo a la derecha, franja amarilla de anotaciones cuando las hay, y lista de datos en dos columnas (término de 6,6rem en etiqueta azul, valor en Body) con divisores de 1px. Estado vacío: «Nuevo porte / Sin calcular», burbuja reducida a 7rem en gris con «— €» y un texto que explica qué hacer.
- **Cuadro de tarifas:** mismo borde y esquinas, sin sombra; cabecera azul en cursiva, filas con divisores de 1px y precio en condensada 800; la fila aplicada se rellena de amarillo con el precio en rojo a 1,3rem; pie gris con el origen de las tarifas.
- **Bloque del mapa:** blanco, borde azul de 2px, 6px de relleno, con la leyenda en etiqueta condensada en tinta suave.

### Inputs / Fields
- **Style:** campos de Streamlit con esquinas de 0,4rem. En la barra lateral, fondo azul campo, texto blanco, borde azul de hoja, etiquetas en rótulo de hoja y marcadores de posición en #BCD0EE. Las etiquetas de campo van en condensada 700 a 0,84rem en mayúsculas.
- **Focus:** anillo azul de 3px con 2px de separación; amarillo dentro de la barra lateral.
- **Error:** el aviso aparece bajo el campo que falla y repite bajo el botón. En la barra lateral, los avisos son bloques blancos con borde rojo de 2px y texto rojo hondo en 600. El operario reconocido se confirma en amarillo; el código no encontrado, en blanco con un punto rojo.

### Navigation
- **Hoja de pedido:** la barra lateral azul es la única navegación. Cada sección se abre con un título en headline blanco y un círculo amarillo de 1,6rem con el número en azul. Al pie, notas de conexión en rótulo de hoja tras una línea de 1px (#3F6DB0).

### Pegatina de estado
Pieza firma del sistema. Flota sobre el borde superior de la ficha (girada 4°), en condensada 800 a 0,95rem en mayúsculas con una segunda línea en 600 a 0,74rem. Pendiente: amarilla con tinta, «Pendiente / de guardar». Registrado: verde con texto blanco, «Registrado» con hora y operario, y entra con una animación de 320ms (cubic-bezier(.16, 1, .3, 1)) desde 14° y escala 1,35; sin animación con reducción de movimiento y en móvil.

### Burbuja del precio
Círculo amarillo de 9,6rem con borde rojo de 5px, girado -7°, con la cifra en Precio rojo y «Precio del porte» en etiqueta tinta debajo.

### Mapa
Callejero en gris apagado (escala de grises, contraste 0,7, brillo 1,16) para que manden los colores de zona. Un anillo por zona en su color (3px y opacidad 0,85; la zona aplicada a 6px y rellena al 14 %). Rótulos en píldora con el color y la tinta de la zona; el de la zona aplicada, más grande y con contorno amarillo de 3px. Ruta en azul de 5px sobre un trazo blanco de 10px. Almacén y destino con su símbolo de anillo y una etiqueta rectangular (4px) en azul o rojo. Controles con borde azul de 2px y sin sombra.

## Do's and Don'ts

### Do:
- **Do** tomar el color y la tinta de cada zona de COLORES_ZONA y TINTAS_ZONA y usarlos igual en mapa, ficha y cuadro.
- **Do** escribir titulares, precios, botones y estados en Barlow Condensed 800 cursiva mayúsculas, y los datos en Barlow normal.
- **Do** separar los bloques del área principal con borde azul de 2px y esquinas de 0,6rem.
- **Do** reservar el amarillo para lo que pide atención: precio, pendiente, aplicado, anotaciones y foco en la hoja.
- **Do** mostrar los errores de validación bajo el campo que falla, en bloque blanco con borde rojo dentro de la hoja azul.
- **Do** usar anillo de foco azul de 3px en el área principal y amarillo en la barra lateral.
- **Do** llevar siempre el logo original (assets/bigmat-rodriguez.png) sobre su placa blanca, sin redibujarlo.

### Don't:
- **Don't** convertir la app en una herramienta gris de oficina ni en un panel de métricas neutro.
- **Don't** usar sombras duras sin desenfoque; toda sombra es difusa y teñida.
- **Don't** inclinar datos, tablas ni campos; el giro es solo para la burbuja, la pegatina y la cinta del subtítulo.
- **Don't** elegir a ojo la tinta del texto sobre un color de zona ni volver al azul de zona 3 anterior (#2B7DE1), que no llegaba a 4,5:1 con blanco.
- **Don't** añadir degradados a los bloques de marca.
