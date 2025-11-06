# AniMatch

**AniMatch** es un pequeño proyecto de recomendaciones de animes.  
El objetivo es poder registrarte, iniciar sesión y obtener recomendaciones según tus puntuaciones.  
Está hecho con Python, Flask, MySQL y un poco de Pandas para el modelo de recomendación.

## Estructura del proyecto
backend/
 - api/           → Contiene la API Flask (login, registro y recomendaciones)
 - console/       → Programa para probarlo desde la terminal
 - dao/           → Conexión y acceso a la base de datos MySQ
 - data/          → Aquí van los CSV (anime.csv y rating.csv)
 - model/         → Entrenamiento y carga del modelo de recomendación
 - models/        → Aquí se guarda el modelo entrenado

Frontend/
 - HTML/
   - auth.html → Pantalla de login / registro
   - home.html → Página principal (recomendaciones)
 - CSS/
   - auth.css
   - home.css
 - JS/
   - auth.js  
   - home.js

## Requerimientos
Antes de ejecutar el proyecto, instla las dependencias necesarias:
```bash
pip install flask mysql-connector-python pandas
```
 
## Datos necesarios (CSV)

Para usar el modelo necesitas descargar los archivos de datos:

**Descarga desde Kaggle:**  
[Anime Recommendations Database](https://www.kaggle.com/datasets/CooperUnion/anime-recommendations-database)

Guarda los dos archivos dentro de la carpeta:
**backend/data/**

→ `anime.csv`  
→ `rating.csv`

*(No están subidos aquí por motivos de tamaño.)*

## Modelo de recomendación

El modelo se entrena a partir de las valoraciones de los usuarios y calcula correlaciones entre animes.  
Cuando lo ejecutas por primera vez, crea un archivo dentro de: **backend/models/model_v1.0.pkl**


Ese archivo es el que después usa la función `get_recommendations()` para generar recomendaciones.

## Base de datos

Es necesario tener una base de datos MySQL llamada **`animatch_db`**  
(la puedes crear fácilmente con **MySQL Workbench**.)

Dentro, crea una tabla llamada `users` con las siguientes columnas:

| Columna   | Tipo         | Otros |
|------------|--------------|--------|
| `id`       | INT          | AUTO_INCREMENT, PRIMARY KEY |
| `username` | VARCHAR(50)  | UNIQUE |
| `password` | VARCHAR(255) |  |
| `role`     | VARCHAR(10)  | (por ejemplo: 'user' o 'admin') |

Por defecto, la conexión en el código usa:
- user = "root"
- password = "root"
- host = "localhost"
- database = "animatch_db"

*(puedes cambiarlo en `dao/conexion_bd.py` si lo necesitas)*

## Cómo ejecutarlo por consola

### 1. Crear el modelo (solo la primera vez)
```bash
cd backend
python model/model.py
```
Esto leerá los CSV, entrenará el modelo y lo guardará en models/.

### 2. Abrir la API
```bash
python api/api.py
```

### 3. Probar desde la consola 
```bash
python console/main.py
```

## Acceder desde el Frontend (web)

Además de la consola, **AniMatch** incluye una interfaz web sencilla (HTML, CSS y JavaScript)  
para registrarte, iniciar sesión y obtener recomendaciones de forma visual.

### Cómo usarlo

1. **Arranca la API Flask** (como en los pasos anteriores):
   ```bash
   python api/api.py
   ```
2. **Abre el navegador en:**
`http://127.0.0.1:5000/`
Verás la pantalla de Auth (login / registro).
Al iniciar sesión, serás redirigido automáticamente a Home.

### **Qué puedes hacer desde la web**
- Iniciar sesión o registrarte con tu usuario de la base de datos.
- Pedir recomendaciones desde un formulario que admite ID o nombre de anime:
    - Puedes mezclar entradas, por ejemplo:
 `{ "Naruto": 9.0, "20": 8.5 }`
- Ver un panel de ejemplos (solo informativo) con títulos populares para orientarte.

## Modo administrador y reentrenamiento del modelo
Si inicias sesión, tanto en cosola como en la web, con:

- usuario: admin
- contraseña: admin

En el menú aparecerá una opción adicional:

`Reentrenar modelo`

Esta opción permite volver a entrenar el modelo utilizando los nuevos archivos CSV  
(`anime.csv` y `rating.csv`) sin necesidad de reiniciar el servidor.  
Es útil si has modificado o reemplazado los archivos de datos y quieres actualizar las recomendaciones.

Durante el reentrenamiento:

- El modelo se recalcula completamente.  
- Se guarda sobre el archivo existente:  
  `backend/models/model_v1.0.pkl`  
- El sistema comenzará a utilizar automáticamente el modelo actualizado.
- **Importante:** este proceso puede tardar varios minutos dependiendo del tamaño de los datos  
  y de la potencia del equipo. **Ten paciencia** y espera a que finalice antes de hacer nuevas peticiones.




