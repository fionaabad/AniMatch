import pandas as pd
import json
import os

# CONFIGURACIÓ DE RUTES (ajustada al teu projecte)

# Aquesta línia obté el directori "backend/"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Carpeta de dades i models dins backend/
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Fitxers de model
MODEL_FILE = os.path.join(MODELS_DIR, "model_v1.0.pkl")
CURRENT_MODEL = os.path.join(MODELS_DIR, "current_model.json")

# PARÀMETRES DE FILTRE
MIN_RATINGS_ITEM = 100      # mínim de valoracions per anime
MIN_RATINGS_USER = 5        # mínim de valoracions per usuari
MIN_PERIODS_CORR = 100      # mínim d’usuaris comuns per calcular correlació


# ENTRENAR ALGORITME
def train_model():
    """Llegeix els CSV, aplica filtres, calcula correlacions i guarda el model"""

    print("Llegint dades...")
    ratings = pd.read_csv(os.path.join(DATA_DIR, "rating.csv"))
    anime = pd.read_csv(os.path.join(DATA_DIR, "anime.csv"))

    # Neteja bàsica
    print("Netejant dades...")
    ratings = ratings[ratings["rating"] != -1]
    ratings = ratings.drop_duplicates(subset=["user_id", "anime_id"])

    # Filtres d'animes
    print(f"Filtres: animes amb > {MIN_RATINGS_ITEM} valoracions...")
    counts_per_anime = ratings["anime_id"].value_counts()
    valid_animes = counts_per_anime[counts_per_anime >= MIN_RATINGS_ITEM].index
    df_filt = ratings[ratings["anime_id"].isin(valid_animes)].copy()

    print("Animes abans del filtre:", ratings["anime_id"].nunique())
    print("Animes despres del filtre:", df_filt["anime_id"].nunique())
    print(f"Files totals despres del filtre: {len(df_filt)}")

    # Filtres d’usuaris (mínim)
    print(f"Filtres: usuaris amb > {MIN_RATINGS_USER} valoracions...")
    counts_user = df_filt["user_id"].value_counts()
    valid_users = counts_user[counts_user >= MIN_RATINGS_USER].index
    df_filt = df_filt[df_filt["user_id"].isin(valid_users)].copy()

    # Filtres d’usuaris (màxim = p99)
    counts_user_after = df_filt["user_id"].value_counts()
    max_ratings_user = int(counts_user_after.quantile(0.99)) if not counts_user_after.empty else 999999
    valid_users = counts_user_after[
        (counts_user_after >= MIN_RATINGS_USER) &
        (counts_user_after <= max_ratings_user)
    ].index
    df_filt = df_filt[df_filt["user_id"].isin(valid_users)].copy()

    print(f"Usuaris finals: {df_filt['user_id'].nunique()}")
    print(f"Files finals despres de tots els filtres: {len(df_filt)}")

    # Taula pivot i correlacions
    print("Creant taula pivot (user x anime)...")
    userRatings = df_filt.pivot_table(index="user_id", columns="anime_id", values="rating")

    print(f"Calculant correlacions (Pearson, min_periods={MIN_PERIODS_CORR})...")
    corrMatrix = userRatings.corr(method="pearson", min_periods=MIN_PERIODS_CORR)

    # Guardar model
    os.makedirs(MODELS_DIR, exist_ok=True)
    corrMatrix.to_pickle(MODEL_FILE)
    with open(CURRENT_MODEL, "w") as f:
        json.dump({"model_version": "1.0", "artifact_path": MODEL_FILE}, f, indent=4)

    print(f"Model guardat a: {MODEL_FILE}")
    print("Entrenament complet (v1.0)")


# CARREGAR ALGORITME
def load_model():
    """Carrega el model entrenat (matriu de correlacions)"""
    if not os.path.exists(CURRENT_MODEL):
        raise FileNotFoundError("No s'ha trobat current_model.json. Entrena el model primer!")

    with open(CURRENT_MODEL) as f:
        info = json.load(f)
    model_path = info["artifact_path"]

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"No existeix el fitxer de model: {model_path}")

    print(f"Carregant model des de: {model_path}")
    corrMatrix = pd.read_pickle(model_path)
    return corrMatrix


# RECOMANAR ANIMES
def get_recommendations(myRatings, top_n=10):
    """
    myRatings: diccionari {anime_id: rating}, ex: {11061: 10, 2476: 1}
    Retorna DataFrame amb (anime_id, score)
    """
    corrMatrix = load_model()
    simCandidates = pd.Series(dtype="float64")

    for anime_id, rating in myRatings.items():
        if anime_id not in corrMatrix.columns:
            continue
        sims = corrMatrix[anime_id].dropna()
        sims = sims.map(lambda x: x * rating)
        simCandidates = pd.concat([simCandidates, sims])

    if simCandidates.empty:
        print("No hi ha candidats similars.")
        return pd.DataFrame(columns=["anime_id", "score"])

    simCandidates = simCandidates.groupby(simCandidates.index).sum()
    simCandidates = simCandidates.drop(myRatings.keys(), errors="ignore")
    top = simCandidates.sort_values(ascending=False).head(top_n)

    result = pd.DataFrame({"anime_id": top.index, "score": top.values})
    # Afegim els noms dels animes
    anime = pd.read_csv(os.path.join(DATA_DIR, "anime.csv"))  # llegim noms
    result = result.merge(anime[["anime_id", "name"]], on="anime_id", how="left")
    result = result[["anime_id", "name", "score"]]  # reordenem columnes

    print("Recomanacions generades!")
    return result


# TEST RÀPID DES DEL TERMINAL
if __name__ == "__main__":
    print("Executant prova rapida de model...")
    # Primer entrenar (només 1 cop)
    train_model()

    # Exemple de recomanacions
    perfil = {11061: 10, 2476: 1}  # Hunter x Hunter = 10, School Days = 1
    recom = get_recommendations(perfil)
    print(recom.head())
