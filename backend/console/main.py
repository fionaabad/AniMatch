import os
import requests

BASE_URL = os.environ.get("ANIMATCH_API", "http://127.0.0.1:5000")
TIMEOUT = 10  # tiempo por defecto (10 segundos)
LOGGED_IN = False
USERNAME = None
USER_ROLE = None  # guardamos el rol (user / admin)


def pedir_json(method, path, body=None, timeout=None):
    """
    Envía una petición HTTP a la API Flask y devuelve (status, data_json).
    Se usa para todas las operaciones: login, registro, recomendaciones, etc.
    """
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


# AUTENTICACIÓN
def registrarse():
    print("\n--- Registro de usuario ---")
    username = input("Usuario: ").strip()
    password = input("Contraseña (mínimo 8 caracteres): ").strip()

    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        return

    status, data = pedir_json("POST", "/register", {"username": username, "password": password})
    if status == 201:
        print("Usuario creado correctamente. Ahora puedes iniciar sesión.")
    else:
        print(data or {"error": "Error durante el registro."})


def iniciar_sesion():
    """Inicia sesión y guarda nombre + rol"""
    print("\n--- Iniciar sesión ---")
    user = input("Usuario: ").strip()
    pw = input("Contraseña: ").strip()

    status, data = pedir_json("POST", "/login", {"username": user, "password": pw})
    if status == 200:
        global LOGGED_IN, USERNAME, USER_ROLE
        LOGGED_IN = True
        USERNAME = data.get("username", user)
        USER_ROLE = data.get("role", "user")
        print(f"Sesión iniciada como {USERNAME} ({USER_ROLE})")
    else:
        print(data or {"error": "Error al iniciar sesión."})


def cerrar_sesion():
    """Cierra la sesión actual"""
    global LOGGED_IN, USERNAME, USER_ROLE
    LOGGED_IN = False
    USERNAME = None
    USER_ROLE = None
    print("Sesión cerrada.")

def existe_anime(anime_id: int) -> bool:
    """Consulta si un anime existe dentro del modelo."""
    status, data = pedir_json("GET", f"/exists-anime/{anime_id}")
    return (status == 200) and bool(data and data.get("exists") is True)


def mostrar_ejemplos():
    """Muestra ejemplos de como introducir los datos."""
    print("\n--- Ejemplos de entrada ---")
    print("→ Solo por ID:")
    print("  { 20: 9.0, 154: 7.5 }")
    print("→ Solo por nombre:")
    print('  { \"Naruto\": 9.0, \"Fullmetal Alchemist: Brotherhood\": 8.5 }')
    print("→ Mixto (ID + nombre):")
    print('  { 20: 9.0, \"Death Note\": 8.0 }')
    print("\n(Puedes escribir nombres o IDs.)\n")


def pedir_par_entrada(idx: int):
    """Pide un anime (por ID o nombre) y una nota del 1 al 10."""
    while True:
        raw = input(f"Anime #{idx} (nombre o ID): ").strip()
        if not raw:
            print("No puede estar vacío.")
            continue
        try:
            aid = int(raw)
            if not existe_anime(aid):
                print("Ese ID no está en el modelo. Prueba otro o escribe el nombre.")
                continue
            clave = aid
            break
        except ValueError:
            clave = raw
            break

    while True:
        nota = input("Nota (1–10): ").strip()
        try:
            r = float(nota)
            if 1 <= r <= 10:
                return clave, r
        except ValueError:
            pass
        print("Debe ser un número entre 1 y 10.")


def resolver_conflictos_y_reintentar(payload_inicial):
    """
    Envía el payload y, si la API devuelve 409 (nombres ambiguos),
    muestra los candidatos y permite elegir el correcto.
    """
    status, data = pedir_json("POST", "/obtener-recomendaciones", payload_inicial)

    if status == 200:
        return status, data

    if status == 409 and isinstance(data, dict) and "conflicts" in data:
        print("\nSe detectaron nombres ambiguos. Elige el correcto:")
        fixed = dict(payload_inicial)
        conflicts = data.get("conflicts") or {}
        for original, candidatos in conflicts.items():
            print(f'\n→ "{original}" coincide con:')
            for i, cand in enumerate(candidatos, start=1):
                print(f"   {i}. [{cand.get('id')}] {cand.get('name')}")
            while True:
                eleccion = input("Elige número o ID manual: ").strip()
                try:
                    val = int(eleccion)
                    if 1 <= val <= len(candidatos):
                        elegido = int(candidatos[val - 1].get("id"))
                        break
                    else:
                        elegido = val
                        break
                except ValueError:
                    print("Entrada no válida.")
            rating = fixed.pop(original)
            fixed[elegido] = rating

        print("\nReintentando con las selecciones elegidas...")
        return pedir_json("POST", "/obtener-recomendaciones", fixed)

    return status, data


def pedir_recomendaciones():
    """Pide dos animes y muestra las recomendaciones."""
    if not LOGGED_IN:
        print("Primero debes iniciar sesión.")
        return

    print("\nIntroduce 2 animes con su nota (1–10).")
    perfil = {}
    for i in range(1, 3):
        k, r = pedir_par_entrada(i)
        perfil[k] = r

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


def reentrenar_modelo():
    """Solo para admin: reentrena el modelo."""
    if USER_ROLE != "admin":
        print("Solo los administradores pueden hacer esto.")
        return

    print("\n--- Reentrenar modelo (admin) ---")
    pw = input("Contraseña de admin: ").strip()

    # Timeout largo (15 minutos)
    LONG_TIMEOUT = 15 * 60
    body = {"username": USERNAME, "password": pw}
    status, data = pedir_json("POST", "/retrain", body, timeout=LONG_TIMEOUT)

    if status == 200:
        print("Modelo reentrenado correctamente.")
    elif status == 403:
        print("No autorizado o contraseña incorrecta.")
    elif status == 409:
        print("Ya hay un reentrenamiento en curso.")
    elif status is None:
        print("Error de conexión.")
    else:
        print(data or {"error": "No se pudo reentrenar el modelo."})


# MENÚS
def menu_acceso():
    """Opciones antes de iniciar sesión."""
    print("\n--- Menú principal ---")
    print("1. Registrarse")
    print("2. Iniciar sesión")
    print("3. Ver ejemplos")
    print("0. Salir")
    return input("Elige opción: ").strip()


def menu_usuario():
    """Opciones una vez logueado."""
    print(f"\n--- Menú (usuario: {USERNAME}) ---")
    print("1. Obtener recomendaciones")
    print("2. Ver ejemplos")
    print("3. Cerrar sesión")
    if USER_ROLE == "admin":
        print("4. Reentrenar modelo (admin)")
    print("0. Salir")
    return input("Elige opción: ").strip()


# PROGRAMA PRINCIPAL
def main():
    print("AniMatch (consola) — pequeño proyecto de recomendaciones de anime")
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
                print("¡Hasta luego!")
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
            elif opcion == "4" and USER_ROLE == "admin":
                reentrenar_modelo()
            elif opcion == "0":
                print("¡Hasta luego!")
                break
            else:
                print("Opción no válida.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSaliendo...")
