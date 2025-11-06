import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from dao.conexion_bd import Conexion
from dao.dao import AnimatchDAO
from model.model import get_recommendations, load_model, train_model

import csv

# (no tocar: están ajustadas para cargar el Frontend desde Flask)
BACKEND_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT  = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
TEMPLATES     = os.path.join(PROJECT_ROOT, "Frontend", "HTML")   
STATIC        = os.path.join(PROJECT_ROOT, "Frontend")           

# Crear app Flask y permitir CORS
app = Flask(__name__, template_folder=TEMPLATES, static_folder=STATIC, static_url_path="/")
CORS(app)

DATA_DIR  = os.path.join(BACKEND_DIR, "data")
ANIME_CSV = os.path.join(DATA_DIR, "anime.csv")

NAME_INDEX = None         # dict, ej: {"naruto": 20}
NAME_LOOKUP_ROWS = None   # lista de dicts, ej: [{"id": 20, "name": "Naruto"}, ...]

def load_name_index():
    """
    Gestionamos nombres a id
    """
    global NAME_INDEX, NAME_LOOKUP_ROWS
    if NAME_INDEX is not None:
        return  # ya estaba cargado

    idx = {}
    rows = []

    try:
        with open(ANIME_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # anime_id -> int
                try:
                    aid = int(row.get("anime_id"))
                except Exception:
                    continue

                # nombre normalizado
                name = (row.get("name") or "").strip()
                if not name:
                    continue

                idx[name.lower()] = aid
                rows.append({"id": aid, "name": name})
    except FileNotFoundError:
        # En el caso que no haya CSV, seguimos acceptando ids
        idx, rows = {}, []

    NAME_INDEX = idx
    NAME_LOOKUP_ROWS = rows


def resolve_name_to_id(name: str):
    """
    Primero busa exacto y despues por contiene. Intentamos convertir el nombre a id.
    """
    load_name_index()  # miramos que el inidice esta cargado
    if not NAME_INDEX:
        return None, []  # no hay índice, osea no hay CSV: seguir por ID

    q = (name or "").strip().lower()
    if not q:
        return None, []

    # 1) miramos si es exacta
    if q in NAME_INDEX:
        return NAME_INDEX[q], []

    # 2) miramos si contiene
    cands = [row for row in NAME_LOOKUP_ROWS if q in row["name"].lower()]
    if len(cands) == 1:
        return cands[0]["id"], []
    if len(cands) > 1:
        # primeor por nombre cortos despues alfabetico
        cands.sort(key=lambda r: (len(r["name"]), r["name"].lower()))
        return None, cands[:10]

    # 3) En caso de no resuktados
    return None, []


# Asi evitamos cargar el modelo cada vez, re rellena al primer uso
MODEL_CACHE = None

def get_model_cached():
    """Devuelve la matriz de correlaciones desde caché (o la carga si está vacía)."""
    global MODEL_CACHE
    if MODEL_CACHE is None:
        MODEL_CACHE = load_model()
    return MODEL_CACHE



# Home: servimos la página de login/registro
@app.route("/")
def index():
    # Frontend/HTML/auth.html
    return render_template("auth.html")


@app.get("/health")
def health():
    """Endpoint simple para comprobar si la API está viva."""
    return jsonify({"status": "ok"}), 200


# AUTH

@app.post("/register")
def register():
    """
    Crea un usuario nuevo.
    Espera JSON: {"username": "blabla", "password": "blabla"}
    La conisdciones:
      - username >= 3 chars
      - password >= 8 chars
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    # Validaciones básicas
    if not username or not password:
        return jsonify({"error": "username y password son obligatorios"}), 400
    if len(username) < 3:
        return jsonify({"error": "el username debe tener al menos 3 caracteres"}), 400
    if len(password) < 8:
        return jsonify({"error": "la password debe tener al menos 8 caracteres"}), 400

    # Insert en BD
    conn = Conexion()
    try:
        ok = AnimatchDAO.add_user(username, password, conn, role="user")
    finally:
        # Cerrar conexión alwayyys
        try:
            conn.GetConn().close()
        except:
            pass

    if ok:
        return jsonify({"message": "usuario creado", "username": username, "role": "user"}), 201
    return jsonify({"error": "username ya existe o error al crear"}), 409


@app.post("/login")
def login():
    """
    Inicia sesión.
    Espera JSON: {"username": "blabla", "password": "blabla"}
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username y password son obligatorios"}), 400

    # buscamos le usuario
    conn = Conexion()
    try:
        user = AnimatchDAO.get_user_by_username(username, conn)
    finally:
        try:
            conn.GetConn().close()
        except:
            pass

    # Ccomporvamos
    if not user or user.get("password") != password:
        return jsonify({"error": "credenciales invalidas"}), 401

    return jsonify({"message": "login ok", "username": user["username"], "role": user["role"]}), 200


# RECOMENDACIONES

@app.post("/obtener-recomendaciones")
def obtener_recomendaciones():
    """
    Genera recomendaciones a partir de un JSON {anime: rating}.
    - 'anime' puede ser id o nombre.
    - 'rating' debe ser número del 1 al 10.
    - Si hay ambigüedad en nombres, devuelve 409 con 'conflicts' para que el front elija.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Envía un JSON {anime_id|anime_name: rating}"}), 400

    perfil = {}      # {anime_id: rating}
    conflicts = {}   # {"texto_original": [{id,name}, ...]}

    for key, rating in data.items():
        # 1) Validamos que sea numero el rating
        try:
            r = float(rating)
        except (TypeError, ValueError):
            return jsonify({"error": f"Rating inválido para '{key}'"}), 400

        # 2) Tratamos a key como id
        try:
            aid = int(str(key).strip())
            perfil[aid] = r
            continue  # siguiente entrada
        except ValueError:
            pass  # no era un número: lo tratamos como nombre

        # 3) resoovemos a nombre -> id (exacto o parcial con candidatos)
        aid, cands = resolve_name_to_id(str(key))
        if aid is not None:
            perfil[aid] = r
        elif cands:
            conflicts[str(key)] = cands  # ambigüedad: devolver lista al front
        else:
            return jsonify({"error": f"No se encontró ningún anime que coincida con '{key}'"}), 404

    # Si hay nombres ambiguos, devolvemos 409 con candidatos
    if conflicts:
        return jsonify({"error": "Múltiples coincidencias de nombre.", "conflicts": conflicts}), 409

    if not perfil:
        return jsonify({"error": "No se proporcionaron pares (anime, rating) válidos"}), 400

    # 4) Llamar al modelo (sin tocar tu get_recommendations)
    try:
        recom = get_recommendations(perfil, top_n=10)
        return jsonify(recom.to_dict(orient="records")), 200
    except FileNotFoundError:
        # Modelo no entrenado aún
        return jsonify({"error": "El modelo no está entrenado. Ejecuta train_model() antes."}), 500
    except Exception as e:
        return jsonify({"error": f"Error: {e}"}), 500


# UTILIDAD: comprobar existencia de anime en el modelo

@app.get("/exists-anime/<int:anime_id>")
def exists_anime(anime_id):
    """
    Devuelve si un anime_id está presente en la matriz de correlación (modelo).
    """
    try:
        corr = get_model_cached()  # usa caché
        cols = corr.columns.tolist()
        exists = int(anime_id) in set(map(int, cols))
        return jsonify({"anime_id": anime_id, "exists": bool(exists)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ADMIN: reentrenar modelo

@app.post("/retrain")
def retrain():
    """
    Reentrena el modelo (solo admin).
    Espera JSON: {"username": "...", "password": "..."}
    - Verifica que el usuario tenga role="admin" y password correcta.
    - Llama a train_model() y recarga la caché con load_model().
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    # 1) Verificar credenciales de admin (usando mi DAO)
    conn = Conexion()
    try:
        user = AnimatchDAO.get_user_by_username(username, conn)
    finally:
        try:
            conn.GetConn().close()
        except:
            pass

    if not user or user.get("role") != "admin" or user.get("password") != password:
        return jsonify({"error": "No autorizado"}), 403

    # 2) Reentrenar y recargar el modelo
    try:
        train_model()               # recalcula y guarda model_v1.0.pkl
        global MODEL_CACHE
        MODEL_CACHE = load_model()  # refresca caché en memoria
        return jsonify({"message": "Modelo reentrenado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Fallo al reentrenar: {e}"}), 500


# ARRANQUE
if __name__ == "__main__":
    app.run(debug=True)
