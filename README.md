# Moneyball for Spurs

An ML-driven scouting toolkit for Tottenham Hotspur’s January transfer window. The pipeline builds per-90 statistical profiles for players, groups them into playing styles, surfaces cheaper lookalikes via cosine similarity, and highlights undervalued targets by comparing model-predicted value to market value. Data sources include Understat, FotMob/Sofascore (through the `soccerdata` package), and open Transfermarkt dataset CSVs.

**Driving question:** Can a machine learning model find undervalued players who fit what Tottenham needs this January?

## Setup

```bash
git clone https://github.com/samvitchoudhary/spurs-moneyball.git
cd spurs-moneyball
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the dashboard

The app reads committed tables in `app_data/`, so a fresh clone does not need a scrape.

```bash
streamlit run app/Home.py
```

If you rebuild the processed tables yourself, refresh those files first:

```bash
python scripts/export_app_data.py
```

## Run the website

The public site is a Next.js app in `web/`. It does no modelling in the browser. It reads JSON exported from the committed dashboard tables.

```bash
python scripts/export_web_data.py
cd web
npm install
npm run dev
```

Open http://localhost:3000. The Streamlit app in `app/` is unchanged and remains the internal tool.

`npm run build` writes a static export to `web/out`.

## Deploy to Vercel

The site is configured with `output: 'export'`, so Vercel serves files and does not need a backend or environment variables.

1. Import this GitHub repository in Vercel.
2. Set the project root directory to `web`.
3. Leave the framework as Next.js. Build command: `npm run build`. Output directory: `out`.
4. Deploy.

Do not point that project at the repository root. The Streamlit dashboard is not part of the Vercel app.

## Project structure

| Path | Purpose |
|------|---------|
| `data/raw/` | Raw downloads from Understat, soccerdata, Transfermarkt, etc. (not committed) |
| `data/processed/` | Cleaned, joined tables ready for modeling (not committed) |
| `notebooks/` | Exploratory analysis and ad hoc experiments |
| `reports/` | Figures, tables, and write-ups for scouting decisions |
| `src/collect.py` | Pull player and match data from external APIs and CSVs |
| `src/clean.py` | Standardize schemas, fix types, and handle missing values |
| `src/join.py` | Link stats, market values, and identity across sources |
| `src/features.py` | Build per-90 and derived feature vectors |
| `src/similarity.py` | Cosine similarity search for stylistic replacements |
| `src/cluster.py` | Cluster players into playing-style groups |
| `src/value_model.py` | Train and score models for predicted vs. market value |
| `src/backtest.py` | Evaluate recommendations on historical transfer outcomes |
| `scripts/export_web_data.py` | Export `app_data/` tables to compact JSON for the website |
| `web/` | Static Next.js site (home and player pages; other routes are placeholders) |
| `app/` | Streamlit dashboard, kept as the internal tool |
