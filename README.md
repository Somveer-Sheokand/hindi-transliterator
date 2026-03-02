# 🇮🇳 Hindi Transliterator — Flask Web App

Convert English-romanized words to Hindi (Devanagari) script in bulk using the
[AI4Bharat XlitEngine](https://github.com/AI4Bharat/IndicXlit).  
Upload a CSV → pick a column → download the enriched file in seconds.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Bulk transliteration** | Process thousands of rows via a background thread |
| **Live progress bar** | Real-time row counter polled every 800 ms |
| **Drag-and-drop upload** | No page reload required |
| **Downloadable output** | Returns the original CSV with a new `hindi_transliteration` column |
| **PyTorch 2.6 safe** | Applies `torch.serialization.add_safe_globals` fix automatically |

---

## 🖥️ Screenshots

```
┌──────────────────────────────────────┐
│  हिन्दी  Hindi Transliterator        │
│  ──────────────────────────────────  │
│  01  Upload CSV File                 │
│     [ Drag & drop / Browse ]         │
│                                      │
│  02  Select Column                   │
│     [ name               ]           │
│                                      │
│     [ Transliterate →    ]           │
│                                      │
│  ████████████░░░░  62%               │
└──────────────────────────────────────┘
```

---

## 🚀 Local Setup

### 1. Clone / download the project

```bash
git clone https://github.com/yourname/hindi-transliterator.git
cd hindi-transliterator
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The first install will download PyTorch (~700 MB) and the AI4Bharat
> model weights (~200 MB). This is a one-time download.

### 4. Run the app

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 📂 Project Structure

```
hindi-transliterator/
│
├── app.py                 # Flask routes + background job runner
├── transliterator.py      # CSVTransliterator class (XlitEngine wrapper)
├── requirements.txt
├── README.md
│
├── templates/
│   └── index.html         # Single-page UI
│
└── static/
    └── style.css          # Dark theme, saffron/green accents
```

---

## ☁️ Deploy on Render (free tier)

### Step 1 — Push to GitHub

```bash
git init && git add . && git commit -m "Initial commit"
git remote add origin https://github.com/yourname/hindi-transliterator.git
git push -u origin main
```

### Step 2 — Create a Render Web Service

1. Go to [https://render.com](https://render.com) and sign in.
2. Click **New → Web Service**.
3. Connect your GitHub repo.
4. Fill in the settings:

| Setting | Value |
|---|---|
| **Environment** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 300` |
| **Instance Type** | Free (or Starter for better performance) |

> ⚠️ **Important:** The AI4Bharat model is large (~900 MB total with PyTorch).
> Render's **free tier has a 512 MB RAM limit**, which is insufficient.
> Use at minimum the **Starter ($7/month)** plan, or deploy on a machine with
> ≥ 2 GB RAM.

### Step 3 — Add a persistent disk (optional but recommended)

Render's ephemeral filesystem means model weights re-download on every deploy.
Add a **Disk** mount at `/root/.cache` (or wherever `ai4bharat` caches models)
to avoid the delay.

### Step 4 — Deploy

Click **Create Web Service**. Render will build and deploy automatically.
The first boot may take 2–3 minutes while model weights are downloaded.

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | Port the Flask dev server listens on |
| `MAX_CONTENT_LENGTH` | 50 MB | Maximum CSV upload size |
| `beam_width` | `5` | XlitEngine beam width (higher = better accuracy, slower) |

---

## 🧪 Example

**Input CSV** (`names.csv`):

| id | name |
|---|---|
| 1 | Rahul |
| 2 | Priya |
| 3 | Mumbai |

**Column entered:** `name`

**Output CSV** (`hindi_transliteration.csv`):

| id | name | hindi_transliteration |
|---|---|---|
| 1 | Rahul | राहुल |
| 2 | Priya | प्रिया |
| 3 | Mumbai | मुम्बई |

---

## 📝 License

MIT — free to use, modify, and distribute.
