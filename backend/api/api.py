import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from dao.conexion_bd import Conexion
from dao.dao import AnimatchDAO
from model.model import get_recommendations, load_model, train_model

# Rutas del frontend relativas a este archivo (backend/api/api.py)
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
TEMPLATES = os.path.join(PROJECT_ROOT, "Frontend", "HTML")
STATIC    = os.path.join(PROJECT_ROOT, "Frontend")

# Servir HTML + estáticos
app = Flask(__name__, template_folder=TEMPLATES, static_folder=STATIC, static_url_path="/")
CORS(app)

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
        return jsonify({"error": "Envía un JSON {anime_id: rating}"}), 400

    perfil = {}
    try:
        for anime_id, rating in data.items():
            perfil[int(anime_id)] = float(rating)
    except ValueError:
        return jsonify({"error": "IDs enteros y ratings numéricos"}), 400

    try:
        # get_recommendations puede usar load_model() internamente.
        # Si quieres forzar caché, puedes adaptar esa función para usar get_model_cached().
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
