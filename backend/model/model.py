import pandas as pd
import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(__file__)) # sacamos directoiro backend

DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# el modelo entrenado
MODEL_FILE = os.path.join(MODELS_DIR, "model_v1.0.pkl")
CURRENT_MODEL = os.path.join(MODELS_DIR, "current_model.json")

# paramteros para filtrar
MIN_RATINGS_ITEM = 100     
MIN_RATINGS_USER = 5        
MIN_PERIODS_CORR = 500      


def train_model():
    """Llegeix els CSV, aplica filtres, calcula correlacions i guarda el model"""
    # leemos csv
    print("Llegint dades...")
    ratings = pd.read_csv(os.path.join(DATA_DIR, "rating.csv"))
    anime = pd.read_csv(os.path.join(DATA_DIR, "anime.csv"))
    # filtrmos
    print("Netejant dades...")
    ratings = ratings[ratings["rating"] != -1]
    ratings = ratings.drop_duplicates(subset=["user_id", "anime_id"])

    print(f"Filtres: animes amb > {MIN_RATINGS_ITEM} valoracions...")
    counts_per_anime = ratings["anime_id"].value_counts()
    valid_animes = counts_per_anime[counts_per_anime >= MIN_RATINGS_ITEM].index
    df_filt = ratings[ratings["anime_id"].isin(valid_animes)].copy()

    print("Animes abans del filtre:", ratings["anime_id"].nunique())
    print("Animes despres del filtre:", df_filt["anime_id"].nunique())
    print(f"Files totals despres del filtre: {len(df_filt)}")

    print(f"Filtres: usuaris amb > {MIN_RATINGS_USER} valoracions...")
    counts_user = df_filt["user_id"].value_counts()
    valid_users = counts_user[counts_user >= MIN_RATINGS_USER].index
    df_filt = df_filt[df_filt["user_id"].isin(valid_users)].copy()

    counts_user_after = df_filt["user_id"].value_counts()
    max_ratings_user = int(counts_user_after.quantile(0.99)) if not counts_user_after.empty else 999999
    valid_users = counts_user_after[
        (counts_user_after >= MIN_RATINGS_USER) &
        (counts_user_after <= max_ratings_user)
    ].index
    df_filt = df_filt[df_filt["user_id"].isin(valid_users)].copy()

    print(f"Usuaris finals: {df_filt['user_id'].nunique()}")
    print(f"Files finals despres de tots els filtres: {len(df_filt)}")
    # pivot table
    print("Creant taula pivot (user x anime)...")
    userRatings = df_filt.pivot_table(index="user_id", columns="anime_id", values="rating")
    # calculamos correlaciones
    print(f"Calculant correlacions (Pearson, min_periods={MIN_PERIODS_CORR})...")
    corrMatrix = userRatings.corr(method="pearson", min_periods=MIN_PERIODS_CORR)

    # guardamso el modelo!!
    os.makedirs(MODELS_DIR, exist_ok=True)
    corrMatrix.to_pickle(MODEL_FILE)
    with open(CURRENT_MODEL, "w") as f:
        json.dump({"model_version": "1.0", "artifact_path": MODEL_FILE}, f, indent=4)

    print(f"Model guardat a: {MODEL_FILE}")
    print("Entrenament complet (v1.0)")


# cargamos el modelo ya enterado
def load_model():
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


# fucnion para recomendar animes
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
    # merge para sacar los nombres
    anime = pd.read_csv(os.path.join(DATA_DIR, "anime.csv"))  
    result = result.merge(anime[["anime_id", "name"]], on="anime_id", how="left")
    result = result[["anime_id", "name", "score"]]  

    print("Recomanacions generades!")
    return result


# testeamos pare ver que funciona
if __name__ == "__main__":
    print("Executant prova rapida de model...")
    train_model()

    perfil = {11061: 10, 2476: 1}  # Hunter x Hunter = 10, School Days = 1
    recom = get_recommendations(perfil)
    print(recom.head())
