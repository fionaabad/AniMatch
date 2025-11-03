# main.py — versión simple con doble menú (corregida y funcional)
import requests

BASE_URL = "http://127.0.0.1:5000"
TIMEOUT = 10

LOGGED_IN = False
USERNAME = None

def pedir_json(method, path, body=None):
    """Llama a la API y devuelve (status_code, dict|None)."""
    url = f"{BASE_URL}{path}"
    try:
        r = requests.request(method, url, json=body, timeout=TIMEOUT)
        try:
            data = r.json()
        except ValueError:
            data = None
        return r.status_code, data
    except requests.RequestException as e:
        print(f"[error] No se pudo conectar con la API: {e}")
        return None, None

def registrarse():
    print("\n--- Registro ---")
    username = input("Usuario: ").strip()
    password = input("Contraseña (min 8): ").strip()
    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        return
    status, data = pedir_json("POST", "/register", {"username": username, "password": password})
    if status == 201:
        print("Registro correcto. Ahora inicia sesión.")
    else:
        print(data or {"error": "No se pudo registrar."})

def iniciar_sesion():
    """Inicia sesión y cambia el estado global."""
    print("\n--- Iniciar sesión ---")
    user = input("Usuario: ").strip()
    pw = input("Contraseña: ").strip()
    status, data = pedir_json("POST", "/login", {"username": user, "password": pw})
    if status == 200:
        global LOGGED_IN, USERNAME
        LOGGED_IN = True
        USERNAME = data.get("username", user)
        print(f"Sesión iniciada. ¡Hola, {USERNAME}!")
    else:
        print(data or {"error": "Login fallido. Revisa credenciales."})

def pedir_recomendaciones():
    """Pide 2 animes con su nota y muestra las recomendaciones."""
    if not LOGGED_IN:
        print("Primero debes iniciar sesión.")
        return
    print("\nIntroduce 2 animes con su nota (1–10).")
    perfil = {}
    for i in range(1, 3):
        # anime_id
        while True:
            raw_id = input(f"anime_id #{i}: ").strip()
            try:
                aid = int(raw_id)
                break
            except ValueError:
                print("El id debe ser un número entero.")
        # rating
        while True:
            raw_rating = input("nota (1–10): ").strip()
            try:
                r = float(raw_rating)
                if 1 <= r <= 10:
                    break
            except ValueError:
                pass
            print("La nota debe ser un número entre 1 y 10.")
        perfil[aid] = r

    status, data = pedir_json("POST", "/obtener-recomendaciones", perfil)
    if status != 200 or data is None:
        print(data or {"error": "No se pudieron obtener recomendaciones."})
        return
    if not data:
        print("Sin resultados. Prueba con otros animes.")
        return

    print("\nRecomendaciones:")
    print(f"{'anime_id':>8}  {'score':>7}  name")
    for rec in data:
        aid = rec.get("anime_id")
        name = rec.get("name", "(sin nombre)")
        score = rec.get("score", 0)
        try:
            score = f"{float(score):.2f}"
        except Exception:
            score = str(score)
        print(f"{aid:>8}  {score:>7}  {name}")

def cerrar_sesion():
    """Cierra sesión y limpia las variables globales."""
    global LOGGED_IN, USERNAME
    LOGGED_IN = False
    USERNAME = None
    print("Sesión cerrada.")

def menu_acceso():
    print("\n--- Menú ---")
    print("1. Registrarse")
    print("2. Iniciar sesión")
    print("0. Salir")
    return input("Elige: ").strip()

def menu_usuario():
    print(f"\n--- Menú (usuario: {USERNAME}) ---")
    print("1. Obtener recomendaciones")
    print("2. Cerrar sesión")
    print("0. Salir")
    return input("Elige: ").strip()

def main():
    print("AniMatch (console) — versión simple")
    while True:
        if not LOGGED_IN:
            opcion = menu_acceso()
            if opcion == "1":
                registrarse()
            elif opcion == "2":
                iniciar_sesion()
            elif opcion == "0":
                print("¡Adiós!")
                break
            else:
                print("Opción no válida.")
        else:
            opcion = menu_usuario()
            if opcion == "1":
                pedir_recomendaciones()
            elif opcion == "2":
                cerrar_sesion()
            elif opcion == "0":
                print("¡Adiós!")
                break
            else:
                print("Opción no válida.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCerrando...")
