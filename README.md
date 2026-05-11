# 🏎️ Raftaar Racer — Full Stack

A browser racing game with user accounts, score tracking, and leaderboards (daily / weekly / monthly / all-time).

## Stack
- **Backend:** Python / Flask
- **Database:** SQLite (persisted on Render disk)
- **Auth:** Username + password (hashed with SHA-256), session tokens
- **Frontend:** Original Raftaar Racer game + auth pages

---

## 🚀 Deploy to Render (Free Tier)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial Raftaar Racer deploy"
git remote add origin https://github.com/YOUR_USERNAME/raftaar-racer.git
git push -u origin main
```

### Step 2 — Create Render Web Service
1. Go to [render.com](https://render.com) → New → **Web Service**
2. Connect your GitHub repo
3. Render will auto-detect `render.yaml` ✅

### Step 3 — Render settings (if not using render.yaml)
| Field | Value |
|-------|-------|
| Environment | Python |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT` |

### Step 4 — Environment Variables
In Render dashboard → Environment:
```
SECRET_KEY   = (click "Generate" for a random value)
DB_PATH      = /opt/render/project/src/raftaar.db
```

### Step 5 — Add a Disk (IMPORTANT for SQLite persistence)
In Render → your service → **Disks** → Add Disk:
```
Name:       raftaar-db
Mount Path: /opt/render/project/src
Size:       1 GB  (free tier allows this)
```

> ⚠️ Without the disk, SQLite data resets on every deploy. The disk keeps it persistent.

---

## 📁 File Structure
```
raftaar_racer/
├── app.py              ← Flask backend (auth + leaderboard API)
├── requirements.txt    ← Flask, gunicorn
├── render.yaml         ← One-click Render deploy config
├── templates/
│   ├── index.html      ← Login / Signup / Leaderboard page
│   └── game.html       ← The game (with score auto-submit)
```

---

## 🔌 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/signup` | No | Create account |
| POST | `/api/login` | No | Login → returns token |
| POST | `/api/logout` | Token | Invalidate session |
| GET | `/api/me` | Token | My profile + stats |
| POST | `/api/scores` | Token | Submit a game score |
| GET | `/api/leaderboard?period=daily\|weekly\|monthly\|all` | No | Global leaderboard |
| GET | `/api/my-scores` | Token | My recent scores |

---

## 🏆 Leaderboard Periods
- **Daily** — last 24 hours
- **Weekly** — last 7 days
- **Monthly** — last 30 days
- **All Time** — all scores ever

---

## 🎮 How It Works
1. User visits `/` → Login or Sign Up
2. After auth, click **PLAY NOW** → goes to `/game`
3. Game runs normally; on game over the score is auto-posted to `/api/scores`
4. Guest mode works too (no score saved to server)
5. Leaderboard updates in real-time on the home page

---

## Local Development
```bash
pip install flask flask-cors gunicorn
python app.py
# Open http://localhost:5000
```
