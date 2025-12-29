# Image Finder (Streamlit + OpenAI + Qdrant)

MVP aplikacji do wyszukiwania obrazów:
- **Text → Image**: opis tekstowy → embedding → Top-K obrazów
- **Image → Image**: obraz → opis (VLM) → embedding → Top-K obrazów

## 1) Instalacja
```bash
pip install -r requirements.txt
```

## 2) Konfiguracja
Skopiuj `.env.example` do `.env` i uzupełnij:
- `OPENAI_API_KEY`
- `QDRANT_URL` (+ opcjonalnie `QDRANT_API_KEY`)

## 3) Qdrant
Najprościej lokalnie (Docker):
```bash
docker run -p 6333:6333 qdrant/qdrant
```

## 4) Seed (stock zdjęć)
Wrzuć zdjęcia do `data/images/` (kilkanaście już jest), a następnie:
```bash
python scripts/seed_stock.py
```

## 5) Uruchomienie aplikacji
```bash
streamlit run app.py
```

## Uwagi projektowe
W MVP stosujemy podejście: **image → caption (VLM) → text embedding**,
bo upraszcza system do jednej przestrzeni wektorowej i działa dobrze w demo.


## Quick quality sanity-check

After seeding and indexing, you can run a simple self-retrieval test:

```bash
python scripts/evaluate_retrieval.py
```

It measures how often an image can retrieve itself in Top-K using its caption as a query.


## Offline / API issues
If AI captioning or embedding fails (e.g. temporary API issues), uploaded images are saved locally and listed under **Pending uploads**. You can retry indexing later.

## Search history
The app stores last ~200 actions in `data/history.json` (local only).


## New in v1.6
- Saved searches (run / delete)
- Compare two searches side-by-side
- Simple quality dashboard based on history
