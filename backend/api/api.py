import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from dao.conexion_bd import Conexion
from dao.dao import AnimatchDAO
from model.model import get_recommendations, load_model, train_model
import csv

# Rutas del frontend relativas a este archivo (backend/api/api.py)
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
TEMPLATES = os.path.join(PROJECT_ROOT, "Frontend", "HTML")
STATIC    = os.path.join(PROJECT_ROOT, "Frontend")

# Servir HTML + estáticos
app = Flask(__name__, template_folder=TEMPLATES, static_folder=STATIC, static_url_path="/")
CORS(app)

DATA_DIR = os.path.join(BACKEND_DIR, "data")
ANIME_CSV = os.path.join(DATA_DIR, "anime.csv")

NAME_INDEX = None          # dict: "naruto" -> 20
NAME_LOOKUP_ROWS = None    # llista de dicts: {"anime_id": 20, "name": "Naruto"}

def load_name_index():
    """Carrega l'índex nom->id des de anime.csv (si existeix)."""
    global NAME_INDEX, NAME_LOOKUP_ROWS
    if NAME_INDEX is not None:
        return

    idx = {}
    rows = []
    try:
        with open(ANIME_CSV, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    aid = int(row.get("anime_id"))
                except Exception:
                    continue
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                idx[name.lower()] = aid
                rows.append({"id": aid, "name": name})
    except FileNotFoundError:
        # Si no hi ha csv, es permetrà només per ID
        idx, rows = {}, []
    NAME_INDEX = idx
    NAME_LOOKUP_ROWS = rows

def resolve_name_to_id(name: str):
    """Retorna (anime_id, candidates). Si hi ha 1 únic match -> (id, []).
    Si múltiples coincidències -> (None, [ {id,name}, ... ]).
    Si no troba res -> (None, [])."""
    load_name_index()
    if not NAME_INDEX:
        return None, []

    q = (name or "").strip().lower()
    if not q:
        return None, []

    # 1) exacte
    if q in NAME_INDEX:
        return NAME_INDEX[q], []

    # 2) parcial (conté)
    cands = [row for row in NAME_LOOKUP_ROWS if q in row["name"].lower()]
    if len(cands) == 1:
        return cands[0]["id"], []
    if len(cands) > 1:
        # ordena candidats de manera amable
        cands.sort(key=lambda r: (len(r["name"]), r["name"].lower()))
        return None, cands[:10]
    return None, []

# Caché de modelo en memoria
MODEL_CACHE = None
def get_model_cached():
    global MODEL_CACHE
    if MODEL_CACHE is None:
        MODEL_CACHE = load_model()
    return MODEL_CACHE


# Home → index.html
@app.route("/")
def index():
    return render_template("auth.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username y password son obligatorios"}), 400
    if len(username) < 3:
        return jsonify({"error": "el username debe tener al menos 3 caracteres"}), 400
    if len(password) < 8:
        return jsonify({"error": "la password debe tener al menos 8 caracteres"}), 400

    conn = Conexion()
    try:
        ok = AnimatchDAO.add_user(username, password, conn, role="user")
    finally:
        try:
            conn.GetConn().close()
        except:
            pass

    if ok:
        return jsonify({"message": "usuario creado", "username": username, "role": "user"}), 201
    return jsonify({"error": "username ya existe o error al crear"}), 409

@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username y password son obligatorios"}), 400

    conn = Conexion()
    try:
        user = AnimatchDAO.get_user_by_username(username, conn)
    finally:
        try:
            conn.GetConn().close()
        except:
            pass

    if not user or user.get("password") != password:
        return jsonify({"error": "credenciales invalidas"}), 401

    return jsonify({"message": "login ok", "username": user["username"], "role": user["role"]}), 200

@app.post("/obtener-recomendaciones")
def obtener_recomendaciones():
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Envía un JSON {anime_id|anime_name: rating}"}), 400

    perfil = {}
    conflicts = {}  # {"texto_original": [{id,name}, ...]}

    for key, rating in data.items():
        # valida rating
        try:
            r = float(rating)
        except (TypeError, ValueError):
            return jsonify({"error": f"Rating inválido para '{key}'"}), 400

        # si la clau és un enter -> id directe
        try:
            aid = int(str(key).strip())
            perfil[aid] = r
            continue
        except ValueError:
            pass

        # si no és enter, assumim NOM
        aid, cands = resolve_name_to_id(str(key))
        if aid is not None:
            perfil[aid] = r
        elif cands:
            conflicts[str(key)] = cands
        else:
            return jsonify({"error": f"No se encontró ningún anime que coincida con '{key}'"}), 404

    if conflicts:
        return jsonify({"error": "Múltiples coincidencias de nombre.", "conflicts": conflicts}), 409

    if not perfil:
        return jsonify({"error": "No se proporcionaron pares (anime, rating) válidos"}), 400

    try:
        recom = get_recommendations(perfil, top_n=10)
        return jsonify(recom.to_dict(orient="records")), 200
    except FileNotFoundError:
        return jsonify({"error": "El modelo no está entrenado. Ejecuta train_model() antes."}), 500
    except Exception as e:
        return jsonify({"error": f"Error: {e}"}), 500


@app.get("/exists-anime/<int:anime_id>")
def exists_anime(anime_id):
    try:
        corr = get_model_cached()  # usa caché
        exists = int(anime_id) in set(map(int, corr.columns.tolist()))
        return jsonify({"anime_id": anime_id, "exists": bool(exists)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.post("/retrain")
def retrain():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    # verificar admin con conexión bien cerrada
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

    try:
        train_model()              # recalcula y SOBREESCRIBE model_v1.0.pkl
        global MODEL_CACHE
        MODEL_CACHE = load_model() # refresca caché
        return jsonify({"message": "Modelo reentrenado correctamente"}), 200
    except Exception as e:
        return jsonify({"error": f"Fallo al reentrenar: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
