# backend/console/main.py
import requests

BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 10  # por si la api tarda o peta

def pedir_json_y_mostrar(method, path, json=None):
    # hace la peticion y muestra algo sencillo
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.request(method, url, json=json, timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"[error] no se pudo conectar: {e}")
        return None, None

    try:
        data = resp.json()
    except ValueError:
        print(f"[{resp.status_code}] (no json)\n{resp.text}")
        return resp.status_code, None

    print(f"[{resp.status_code}] {data}")
    return resp.status_code, data

def registrar():
    username = input("nombre de usuario: ").strip()
    password = input("contrasena (min 8): ").strip()
    status, _ = pedir_json_y_mostrar("POST", "/register", {"username": username, "password": password})
    return status == 201

def login():
    username = input("nombre de usuario: ").strip()
    password = input("contrasena: ").strip()
    status, data = pedir_json_y_mostrar("POST", "/login", {"username": username, "password": password})
    if status == 200 and data:
        print(f"hola {data.get('username')} (rol: {data.get('role')})")
        return data.get("username"), data.get("role")
    return None, None

def pedir_id_valido(prompt):
    # pide un id y comprueba que existe en el modelo
    while True:
        raw = input(prompt).strip()
        try:
            aid = int(raw)
        except ValueError:
            print("[error] el id debe ser un numero entero")
            continue

        try:
            r = requests.get(f"{BASE_URL}/exists-anime/{aid}", timeout=TIMEOUT)
        except requests.RequestException as e:
            print(f"[error] no se pudo conectar a la api: {e}")
            continue

        try:
            data = r.json()
        except ValueError:
            print("respuesta no json:\n", r.text)
            continue

        if r.status_code == 200 and data.get("exists") is True:
            return aid
        else:
            print("este anime_id no esta en el modelo, prueba otro")

def pedir_rating(prompt):
    # pide una nota 1 al 10
    while True:
        raw = input(prompt).strip()
        try:
            rating = float(raw)
            if 1 <= rating <= 10:
                return rating
        except ValueError:
            pass
        print("la nota debe ser un numero entre 1 y 10")

def obtener_recomendaciones():
    print("Escribe tus 2 animes y su puntación sobre 10 (comprobamos que existan en el modelo)")
    a1 = pedir_id_valido("primer anime_id: ")
    n1 = pedir_rating("nota 1 (1-10): ")
    a2 = pedir_id_valido("segundo anime_id: ")
    n2 = pedir_rating("nota 2 (1-10): ")

    payload = {a1: n1, a2: n2}
    try:
        resp = requests.post(f"{BASE_URL}/obtener-recomendaciones", json=payload, timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"[error] no se pudo conectar a la api: {e}")
        return

    print(f"[{resp.status_code}]")
    try:
        data = resp.json()
    except ValueError:
        print("respuesta no json:\n", resp.text)
        return

    if resp.status_code == 200 and data:
        print("recomendaciones:")
        for rec in data:
            aid = rec.get("anime_id")
            name = rec.get("name", "(sin nombre)")
            score = rec.get("score", 0)
            try:
                print(f"- {aid} | {name} | {float(score):.2f}")
            except (TypeError, ValueError):
                print(f"- {aid} | {name} | {score}")
    elif resp.status_code == 200 and not data:
        print("sin recomendaciones para esos ids, prueba otros")
    else:
        print("error:", data)

def mostrar_menu():
    print("\n--- menu ---")
    print("1. registrarse")
    print("2. iniciar sesion")
    print("3. obtener recomendaciones")
    print("0. salir")
    return input("elige opcion: ").strip()

def main():
    while True:
        op = mostrar_menu()
        if op == "1":
            registrar()
        elif op == "2":
            login()
        elif op == "3":
            obtener_recomendaciones()
        elif op == "0":
            print("chao :)")
            break
        else:
            print("opcion no valida")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ncerrando...")
