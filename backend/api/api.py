   
from dao.conexion_bd import Conexion
from dao.dao import AnimatchDAO
from flask import Flask, jsonify, request, render_template
from model.model import get_recommendations, load_model


app = Flask(__name__)

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

    conn = Conexion()  # root, root
    try:
        ok = AnimatchDAO.add_user(username, password, conn, role="user")
    finally:
        try:
            conn.GetConn().close()
        except:
            pass

    if ok:
        return jsonify({"message": "usuario creado", "username": username, "role": "user"}), 201
    else:
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

    return render_template("../Frontend/HTML/landing_page_2.html")


@app.post("/obtener-recomendaciones")
def obtener_recomendaciones():
    data = request.get_json(silent=True) # llegim el missatge

    if not data or not isinstance(data, dict):
        return jsonify({"error": "Has d'enviar un JSON amb els teus animes i puntuacions"}), 400

    # Convertim les claus i valors a números (int i float)
    perfil = {}
    for anime_id, rating in data.items():
        try:
            perfil[int(anime_id)] = float(rating)
        except ValueError:
            return jsonify({"error": "Els identificadors han de ser enters i les puntuacions numèriques"}), 400

    try:
        recom = get_recommendations(perfil, top_n=10)
        resultat = recom.to_dict(orient="records") # convertim el df en llista de dict per enviar com a JSON
        return jsonify(resultat), 200

    except FileNotFoundError:
        return jsonify({"error": "El model no està entrenat. Executa train_model() abans."}), 500
    except Exception as e:
        return jsonify({"error": f"S'ha produït un error: {str(e)}"}), 500


@app.get("/exists-anime/<int:anime_id>")
def exists_anime(anime_id):
    try:
        corr = load_model()
        exists = int(anime_id) in set(map(int, corr.columns.tolist()))
        return jsonify({"anime_id": anime_id, "exists": bool(exists)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)