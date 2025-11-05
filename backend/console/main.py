# main.py — consola con soporte de nombres, resolución de conflictos y reentrenamiento admin
import os
import requests

BASE_URL = os.environ.get("ANIMATCH_API", "http://127.0.0.1:5000")
TIMEOUT = 10  # por defecto 10 s

LOGGED_IN = False
USERNAME = None

# ---------- Utilidades HTTP ----------
def pedir_json(method, path, body=None, timeout=None):
    """Lanza una petición y devuelve (status, data_json)"""
    url = f"{BASE_URL}{path}"
    try:
        r = requests.request(method, url, json=body, timeout=timeout or TIMEOUT)
        try:
            data = r.json()
        except ValueError:
            data = None
        return r.status_code, data
    except requests.RequestException as e:
        print(f"[error] No se pudo conectar con la API: {e}")
        return None, None

# ---------- Auth ----------
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

def cerrar_sesion():
    global LOGGED_IN, USERNAME
    LOGGED_IN = False
    USERNAME = None
    print("Sesión cerrada.")

# ---------- Ayudas de negocio ----------
def existe_anime(anime_id: int) -> bool:
    """Pregunta a la API si el anime_id está en el modelo."""
    status, data = pedir_json("GET", f"/exists-anime/{anime_id}")
    return (status == 200) and bool(data and data.get("exists") is True)

def mostrar_ejemplos():
    print("\n--- Ejemplos de entrada (IDs y nombres) ---")
    print("• Solo IDs:")
    print("  { 20: 9.0, 154: 7.5 }")
    print("• Solo nombres:")
    print('  { "Naruto": 9.0, "Fullmetal Alchemist: Brotherhood": 8.5 }')
    print("• Mixto (ID + nombre):")
    print('  { 20: 9.0, "Death Note": 8.0 }')
    print("\nConsejos:")
    print("- Si escribes un NOMBRE ambiguo, te mostraré candidatos para elegir.")
    print("- Si escribes un ID que no está en el modelo, te pediré otro.\n")

def pedir_par_entrada(idx: int):
    """Pide una clave (ID o nombre) y una nota [1–10]."""
    while True:
        raw = input(f"Anime #{idx} (ID o nombre): ").strip()
        if not raw:
            print("No puede estar vacío.")
            continue
        try:
            aid = int(raw)
            if not existe_anime(aid):
                print("Ese anime_id NO está en el modelo. Prueba otro o usa el nombre.")
                continue
            clave = aid
            break
        except ValueError:
            clave = raw
            break

    while True:
        raw_rating = input("Nota (1–10): ").strip()
        try:
            r = float(raw_rating)
            if 1 <= r <= 10:
                return clave, r
        except ValueError:
            pass
        print("La nota debe ser un número entre 1 y 10.")

def resolver_conflictos_y_reintentar(payload_inicial):
    """Gestiona el 409 de conflictos de nombres y reintenta automáticamente."""
    status, data = pedir_json("POST", "/obtener-recomendaciones", payload_inicial)

    if status == 200:
        return status, data

    if status == 409 and isinstance(data, dict) and "conflicts" in data:
        print("\nSe detectaron nombres ambiguos. Elige el ID correcto por cada uno:")
        fixed = dict(payload_inicial)
        conflicts = data.get("conflicts") or {}
        for original_text, candidatos in conflicts.items():
            print(f'\n→ "{original_text}" coincide con varios títulos:')
            for i, cand in enumerate(candidatos, start=1):
                print(f"   {i}. [{cand.get('id')}] {cand.get('name')}")
            choice = None
            while True:
                raw = input("Elige opción (número de la lista) o escribe un ID manual: ").strip()
                if not raw:
                    print("No puede estar vacío.")
                    continue
                try:
                    manual_id = int(raw)
                    choice = manual_id
                    break
                except ValueError:
                    pass
                try:
                    idx = int(raw)
                    if 1 <= idx <= len(candidatos):
                        choice = int(candidatos[idx - 1].get("id"))
                        break
                except ValueError:
                    pass
                print("Entrada no válida.")
            rating = fixed.pop(original_text)
            fixed[choice] = rating

        print("\nReintentando con las selecciones realizadas...")
        return pedir_json("POST", "/obtener-recomendaciones", fixed)

    return status, data

def pedir_recomendaciones():
    if not LOGGED_IN:
        print("Primero debes iniciar sesión.")
        return

    print("\nIntroduce al menos 2 animes con su nota (1–10).")
    print("Puedes mezclar IDs y nombres. Con nombres ambiguos, te mostraré candidatos.")
    perfil = {}
    for i in range(1, 3):
        clave, rating = pedir_par_entrada(i)
        perfil[clave] = rating

    status, data = resolver_conflictos_y_reintentar(perfil)

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

# ---------- Reentrenar modelo (solo admin) ----------
def reentrenar_modelo():
    """Permite a un usuario admin reentrenar el modelo."""
    if not LOGGED_IN:
        print("Primero debes iniciar sesión.")
        return

    print("\n--- Reentrenar modelo (admin) ---")
    pw = input("Contraseña de admin: ").strip()

    # usamos timeout largo solo para esta operación (15 minutos)
    LONG_TIMEOUT = 15 * 60

    body = {"username": USERNAME, "password": pw}
    status, data = pedir_json("POST", "/retrain", body, timeout=LONG_TIMEOUT)

    if status == 200:
        print(data.get("message", "Modelo reentrenado correctamente."))
    elif status == 403:
        print("No autorizado: o no eres admin o la contraseña es incorrecta.")
    elif status == 409:
        print(data.get("error", "Ya hay un reentrenamiento en curso."))
    elif status is None:
        print("No se pudo conectar con la API.")
    else:
        print(data or {"error": "No se pudo reentrenar el modelo."})

# ---------- Menús ----------
def menu_acceso():
    print("\n--- Menú ---")
    print("1. Registrarse")
    print("2. Iniciar sesión")
    print("3. Ver ejemplos de entrada")
    print("0. Salir")
    return input("Elige: ").strip()

def menu_usuario():
    print(f"\n--- Menú (usuario: {USERNAME}) ---")
    print("1. Obtener recomendaciones")
    print("2. Ver ejemplos de entrada")
    print("3. Cerrar sesión")
    print("4. Reentrenar modelo (admin)")
    print("0. Salir")
    return input("Elige: ").strip()

# ---------- Main Loop ----------
def main():
    print("AniMatch (console) — IDs y nombres con resolución de conflictos")
    while True:
        if not LOGGED_IN:
            opcion = menu_acceso()
            if opcion == "1":
                registrarse()
            elif opcion == "2":
                iniciar_sesion()
            elif opcion == "3":
                mostrar_ejemplos()
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
                mostrar_ejemplos()
            elif opcion == "3":
                cerrar_sesion()
            elif opcion == "4":
                reentrenar_modelo()
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
