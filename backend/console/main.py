# backend/console/main.py
import requests

BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 10  # segundos para evitar que se quede colgado

def pedir_json_y_mostrar(method, path, json=None):
    """Hace una petición y muestra respuesta de forma segura (maneja no-JSON)."""
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(method, url, json=json, timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"[ERROR] No se pudo conectar con la API: {e}")
        return None, None

    # Intenta parsear JSON; si no, muestra texto crudo
    try:
        data = resp.json()
    except ValueError:
        print(f"[{resp.status_code}] (no JSON)\n{resp.text}")
        return resp.status_code, None

    # Muestra resumen básico y devuelve
    print(f"[{resp.status_code}] {data}")
    return resp.status_code, data

def registrar():
    username = input("Nom d'usuari: ").strip()
    password = input("Contrasenya (min 8 caràcters): ").strip()
    status, _ = pedir_json_y_mostrar("POST", "/register", {"username": username, "password": password})
    return status == 201

def login():
    username = input("Nom d'usuari: ").strip()
    password = input("Contrasenya: ").strip()
    status, data = pedir_json_y_mostrar("POST", "/login", {"username": username, "password": password})
    if status == 200 and data:
        print(f"Benvinguda/benvingut, {data.get('username')} (rol: {data.get('role')})")
        return data.get("username"), data.get("role")
    return None, None

def pedir_id_valido(prompt):
    while True:
        raw = input(prompt).strip()
        try:
            aid = int(raw)
        except ValueError:
            print("[ERROR] L'ID ha de ser un enter.")
            continue

        try:
            r = requests.get(f"{BASE_URL}/exists-anime/{aid}", timeout=TIMEOUT)
        except requests.RequestException as e:
            print(f"[ERROR] No es pot connectar amb la API: {e}")
            continue

        try:
            data = r.json()
        except ValueError:
            print("Resposta no JSON:\n", r.text)
            continue

        if r.status_code == 200 and data.get("exists") is True:
            return aid
        else:
            print("Aquest anime_id NO està al model. Prova un altre (o usa /buscar-anime a la web).")

def pedir_rating(prompt):
    while True:
        raw = input(prompt).strip()
        try:
            rating = float(raw)
            if 1 <= rating <= 10:
                return rating
        except ValueError:
            pass
        print("La nota ha de ser un número entre 1 i 10.")

def obtenir_recomanacions():
    print("Introdueix dos animes i les teves notes. Validarem que existeixin al model.")
    a1 = pedir_id_valido("Primer anime_id: ")
    n1 = pedir_rating("Nota 1 (1-10): ")
    a2 = pedir_id_valido("Segon anime_id: ")
    n2 = pedir_rating("Nota 2 (1-10): ")

    payload = {a1: n1, a2: n2}
    try:
        resp = requests.post(f"{BASE_URL}/obtener-recomendaciones", json=payload, timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"[ERROR] No es pot connectar amb la API: {e}")
        return

    print(f"[{resp.status_code}]")
    try:
        data = resp.json()
    except ValueError:
        print("Resposta no JSON:\n", resp.text)
        return

    if resp.status_code == 200 and data:
        print("Recomanacions:")
        for rec in data:
            aid = rec.get("anime_id")
            name = rec.get("name", "(sense nom)")
            score = rec.get("score", 0)
            try:
                print(f"- {aid} | {name} | {float(score):.2f}")
            except (TypeError, ValueError):
                print(f"- {aid} | {name} | {score}")
    elif resp.status_code == 200 and not data:
        print("Sense recomanacions per aquests IDs (pocs veïns comuns). Prova amb uns altres.")
    else:
        print("Error:", data)

def mostrar_menu():
    print("\n--- MENÚ ---")
    print("1. Registrar-se")
    print("2. Iniciar sessió")
    print("3. Obtenir recomanacions")
    print("0. Sortir")
    return input("Tria una opció: ").strip()

def main():
    while True:
        op = mostrar_menu()
        if op == "1":
            registrar()
        elif op == "2":
            login()
        elif op == "3":
            obtenir_recomanacions()
        elif op == "0":
            print("Adeu!")
            break
        else:
            print("Opció no vàlida.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTancant…")
