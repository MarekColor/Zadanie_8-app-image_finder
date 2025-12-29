# Image Finder  
**Streamlit · OpenAI · Qdrant**

Aplikacja typu MVP do wyszukiwania obrazów z wykorzystaniem embeddingów wektorowych.

Obsługiwane tryby:
- **Text → Image** – opis tekstowy → embedding → Top-K obrazów  
- **Image → Image** – obraz → opis (VLM) → embedding → Top-K obrazów  

Projekt został przygotowany jako rozwiązanie zadania w ramach kursu *Pracuj w AI: Zostań Data Scientist od Zera*.

---

## Funkcjonalności
- galeria obrazów (stock + obrazy użytkownika),
- dodawanie i indeksowanie nowych obrazów,
- wyszukiwanie semantyczne (tekst → obraz),
- wyszukiwanie podobnych obrazów (obraz → obraz),
- historia wyszukiwań,
- zapisane wyszukiwania,
- obsługa błędów i retry indeksowania.

---

## Struktura projektu
.
├── app.py # główna aplikacja Streamlit
├── src/ # logika aplikacji
│ ├── features/ # embeddingi i przetwarzanie obrazu
│ ├── services/ # OpenAI, Qdrant
│ ├── ui/ # zakładki UI
│ └── utils/ # narzędzia pomocnicze
├── data/
│ ├── images/ # obrazy (stock + user)
│ └── history.json # lokalna historia (runtime)
├── scripts/
│ ├── seed_stock.py # indeksowanie zdjęć startowych
│ └── evaluate_retrieval.py
├── notebooks/ # notatniki projektowe
├── requirements.txt
├── runtime.txt
└── .env.example


---

## Instalacja
Zalecane jest użycie wirtualnego środowiska Pythona.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

Konfiguracja

Skopiuj plik .env.example do .env i uzupełnij:

OPENAI_API_KEY=YOUR_OPENAI_KEY
QDRANT_URL=http://localhost:6333   # opcjonalnie
QDRANT_API_KEY=                   # opcjonalnie


Uwaga: plik .env nie powinien być commitowany do repozytorium.

Qdrant – baza wektorowa
Opcja A: Qdrant lokalny (zalecane do demo)

Aplikacja może działać w trybie Qdrant Local (embedded) – bez Dockera i bez serwera.

Opcja B: Qdrant z Dockerem

Jeśli masz Docker Desktop:

docker run -p 6333:6333 qdrant/qdrant

Seed danych (zdjęcia startowe)

W repozytorium znajduje się kilka przykładowych obrazów w data/images/.

Aby je zindeksować:

python scripts/seed_stock.py

Uruchomienie aplikacji
streamlit run app.py


Aplikacja uruchomi się domyślnie pod adresem:
http://localhost:8501

Ocena jakości (opcjonalnie)

Prosty test self-retrieval:

python scripts/evaluate_retrieval.py


Sprawdza, czy obraz potrafi odnaleźć sam siebie w Top-K na podstawie własnego opisu.

Uwagi projektowe

Zastosowano podejście image → caption → text embedding, aby korzystać z jednej przestrzeni wektorowej.

Dane runtime (history.json, pending_uploads.json) są lokalne i nie powinny być wersjonowane.

Projekt ma charakter demonstracyjny (MVP).

Autor

MarekColor
Repozytorium:
https://github.com/MarekColor/Zadanie_8-app-image_finder