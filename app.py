import streamlit as st
from pymongo import MongoClient
import pandas as pd

# ─── Configuración ───
st.set_page_config(page_title="Airbnb Explorer", page_icon="🏠", layout="wide")

st.title("🏠 Airbnb Explorer — Sample Dataset")
st.caption("Consulta alojamientos desde MongoDB Atlas")

# ─── URI desde secrets ───
try:
    mongo_uri = st.secrets["mongo"]["uri"]
except KeyError:
    st.error("Falta configurar mongo.uri en secrets.toml")
    st.stop()

# ─── Conexión ───
@st.cache_resource
def get_client(uri):
    return MongoClient(uri)

try:
    client = get_client(mongo_uri)
    db = client["sample_airbnb"]
    col = db["listingsAndReviews"]
    client.admin.command("ping")
    st.sidebar.success("✅ Conectado a MongoDB Atlas")
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# ─── Filtros ───
st.sidebar.header("🔎 Filtros")

nombre = st.sidebar.text_input("Buscar por nombre")
pais = st.sidebar.text_input("País (ej: Brazil, Spain)")
precio_max = st.sidebar.slider("Precio máximo", 0, 1000, 200)

limite = st.sidebar.selectbox("Resultados", [5, 10, 20, 50], index=1)

# ─── Query dinámica ───
query = {}

if nombre:
    query["name"] = {"$regex": nombre, "$options": "i"}

if pais:
    query["address.country"] = {"$regex": pais, "$options": "i"}

query["price"] = {"$lte": precio_max}

# ─── Ejecutar consulta ───
results = list(col.find(query).limit(limite))

if not results:
    st.warning("No se encontraron resultados")
    st.stop()

st.success(f"Se encontraron {len(results)} alojamientos")

# ─── Procesar datos ───
data = []

for r in results:
    coord = r.get("address", {}).get("location", {}).get("coordinates", [])

    data.append({
        "Nombre": r.get("name", "—"),
        "Precio": r.get("price", "—"),
        "Tipo": r.get("property_type", "—"),
        "País": r.get("address", {}).get("country", "—"),
        "Rating": r.get("review_scores", {}).get("review_scores_rating", "—"),
        "Longitud": coord[0] if len(coord) >= 2 else None,
        "Latitud": coord[1] if len(coord) >= 2 else None,
    })

df = pd.DataFrame(data)

# ─── Tabla ───
st.markdown("### 📋 Resultados")
st.dataframe(df, use_container_width=True)

# ─── Mapa ───
df_map = df.dropna(subset=["Latitud", "Longitud"]).rename(
    columns={"Latitud": "latitude", "Longitud": "longitude"}
)

if not df_map.empty:
    st.markdown("### 🗺️ Mapa")
    st.map(df_map[["latitude", "longitude"]])

# ─── Detalle ───
st.markdown("### 📝 Detalles")

for i, r in enumerate(results):
    with st.expander(r.get("name", "Sin nombre")):
        st.write(f"💰 Precio: {r.get('price', '—')}")
        st.write(f"🏠 Tipo: {r.get('property_type', '—')}")
        st.write(f"🌍 País: {r.get('address', {}).get('country', '—')}")
        st.write(f"⭐ Rating: {r.get('review_scores', {}).get('review_scores_rating', '—')}")

        amenities = r.get("amenities", [])
        if amenities:
            st.write("🧩 Amenidades:", ", ".join(amenities[:10]))