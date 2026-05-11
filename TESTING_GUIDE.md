# Raftaar Racer — API & Database Testing Guide
### Tool: Postman | Database: SQLite

---

## SETUP

### 1. Install Postman
Download free from → https://www.postman.com/downloads/

### 2. Set your Base URL
In Postman, create an **Environment** (top-right → Environments → Add):

| Variable | Local | Render (live) |
|----------|-------|----------------|
| `base_url` | `http://localhost:5000` | `https://your-app.onrender.com` |
| `token` | *(filled automatically by tests)* | *(same)* |

Switch between Local / Render in the top-right dropdown.

### 3. Run app locally (for local testing)
```bash
cd raftaar_racer
pip install flask flask-cors
python app.py
# → Running on http://localhost:5000
```

---

## ═══════════════════════════════════════
## PART 1 — API TESTS (Postman)
## ═══════════════════════════════════════

Create a **Collection** called `Raftaar Racer` and add each request below.

---

### TEST 1 — Sign Up (POST)
```
Method : POST
URL    : {{base_url}}/api/signup
```
**Headers tab:**
```
Content-Type : application/json
```
**Body tab → raw → JSON:**
```json
{
  "username": "TestPlayer1",
  "password": "Test123"
}
```
**Tests tab (paste this script):**
```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
pm.test("Returns token", () => {
    const json = pm.response.json();
    pm.expect(json.token).to.be.a('string');
    pm.expect(json.username).to.eql("TestPlayer1");
    // Save token for all future requests
    pm.environment.set("token", json.token);
});
```
**Expected response:**
```json
{
  "token": "a3f9...64 hex chars...",
  "username": "TestPlayer1"
}
```

---

### TEST 2 — Sign Up Validation (POST) — should FAIL
Test each bad password one at a time:

```
Method : POST
URL    : {{base_url}}/api/signup
```
**Body (test each separately):**
```json
{ "username": "TestPlayer2", "password": "abc" }
```
→ Expected: `400` — "at least 6 characters"

```json
{ "username": "TestPlayer2", "password": "test 123" }
```
→ Expected: `400` — "no spaces"

```json
{ "username": "TestPlayer2", "password": "testtest" }
```
→ Expected: `400` — "one uppercase letter"

```json
{ "username": "TestPlayer2", "password": "TESTTEST" }
```
→ Expected: `400` — "one lowercase letter"

```json
{ "username": "TestPlayer2", "password": "TestTest" }
```
→ Expected: `400` — "one number"

```json
{ "username": "TestPlayer2", "password": "Test@123" }
```
→ Expected: `400` — "no symbols"

```json
{ "username": "TestPlayer1", "password": "Test123" }
```
→ Expected: `409` — "Username already taken"

**Tests tab script:**
```javascript
pm.test("Status is 400 or 409", () => {
    pm.expect(pm.response.code).to.be.oneOf([400, 409]);
});
pm.test("Error message returned", () => {
    pm.expect(pm.response.json().error).to.be.a('string');
});
```

---

### TEST 3 — Login (POST)
```
Method : POST
URL    : {{base_url}}/api/login
```
**Body:**
```json
{
  "username": "TestPlayer1",
  "password": "Test123"
}
```
**Tests tab:**
```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
pm.test("Token returned and saved", () => {
    const json = pm.response.json();
    pm.expect(json.token).to.be.a('string');
    pm.environment.set("token", json.token);
    console.log("Token saved:", json.token);
});
```

---

### TEST 4 — Login with Wrong Password (POST) — should FAIL
```
Method : POST
URL    : {{base_url}}/api/login
```
**Body:**
```json
{
  "username": "TestPlayer1",
  "password": "WrongPass99"
}
```
**Tests tab:**
```javascript
pm.test("Status is 401", () => pm.response.to.have.status(401));
pm.test("Error says invalid credentials", () => {
    pm.expect(pm.response.json().error).to.include("Invalid");
});
```

---

### TEST 5 — Get My Profile (GET)
```
Method : GET
URL    : {{base_url}}/api/me
```
**Headers tab:**
```
Authorization : Bearer {{token}}
```
**Tests tab:**
```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
pm.test("Profile data correct", () => {
    const json = pm.response.json();
    pm.expect(json.username).to.eql("TestPlayer1");
    pm.expect(json.games).to.be.a('number');
    pm.expect(json.best).to.be.a('number');
    console.log("Profile:", JSON.stringify(json));
});
```
**Expected response:**
```json
{
  "username": "TestPlayer1",
  "games": 0,
  "best": 0,
  "total_coins": 0
}
```

---

### TEST 6 — Get Profile Without Token (GET) — should FAIL
```
Method : GET
URL    : {{base_url}}/api/me
```
*(No Authorization header)*

**Tests tab:**
```javascript
pm.test("Status is 401", () => pm.response.to.have.status(401));
pm.test("Unauthorized error", () => {
    pm.expect(pm.response.json().error).to.eql("Unauthorized");
});
```

---

### TEST 7 — Submit a Score (POST)
```
Method : POST
URL    : {{base_url}}/api/scores
```
**Headers tab:**
```
Content-Type  : application/json
Authorization : Bearer {{token}}
```
**Body:**
```json
{
  "score": 1250,
  "coins": 18,
  "level": 4
}
```
**Tests tab:**
```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
pm.test("Score accepted", () => {
    pm.expect(pm.response.json().ok).to.be.true;
});
```

Submit a few more scores to populate the leaderboard:
```json
{ "score": 3400, "coins": 42, "level": 9 }
{ "score": 780,  "coins": 9,  "level": 2 }
```

---

### TEST 8 — Submit Invalid Score (POST) — should FAIL
```
Method : POST
URL    : {{base_url}}/api/scores
```
**Body:**
```json
{ "score": 99999999, "coins": 0, "level": 1 }
```
**Tests tab:**
```javascript
pm.test("Status is 400", () => pm.response.to.have.status(400));
```

---

### TEST 9 — Get Leaderboard (GET) — no auth needed
Test all four periods:

```
Method : GET
URL    : {{base_url}}/api/leaderboard?period=daily
URL    : {{base_url}}/api/leaderboard?period=weekly
URL    : {{base_url}}/api/leaderboard?period=monthly
URL    : {{base_url}}/api/leaderboard?period=all
```
**Tests tab:**
```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
pm.test("Returns array", () => {
    const json = pm.response.json();
    pm.expect(json).to.be.an('array');
    if(json.length > 0) {
        pm.expect(json[0]).to.have.property('username');
        pm.expect(json[0]).to.have.property('best_score');
        pm.expect(json[0]).to.have.property('games_played');
        // First entry should be the highest score
        console.log("Top player:", json[0].username, "Score:", json[0].best_score);
    }
});
```
**Expected response:**
```json
[
  {
    "username": "TestPlayer1",
    "best_score": 3400,
    "games_played": 3,
    "max_level": 9
  }
]
```

---

### TEST 10 — Get My Score History (GET)
```
Method : GET
URL    : {{base_url}}/api/my-scores
```
**Headers tab:**
```
Authorization : Bearer {{token}}
```
**Tests tab:**
```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
pm.test("Score history returned", () => {
    const json = pm.response.json();
    pm.expect(json).to.be.an('array');
    pm.expect(json.length).to.be.at.least(1);
    pm.expect(json[0]).to.have.property('score');
    pm.expect(json[0]).to.have.property('played_at');
    // Should be sorted newest first
    console.log("My scores:", json.map(s => s.score));
});
```

---

### TEST 11 — Logout (POST)
```
Method : POST
URL    : {{base_url}}/api/logout
```
**Headers tab:**
```
Authorization : Bearer {{token}}
```
**Tests tab:**
```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
pm.test("Logout confirmed", () => {
    pm.expect(pm.response.json().ok).to.be.true;
});
```

---

### TEST 12 — Use Token After Logout (GET) — should FAIL
```
Method : GET
URL    : {{base_url}}/api/me
```
**Headers tab:**
```
Authorization : Bearer {{token}}
```
**Tests tab:**
```javascript
pm.test("Status is 401 after logout", () => pm.response.to.have.status(401));
```

---

## ═══════════════════════════════════════
## PART 2 — DATABASE TESTS (SQLite)
## ═══════════════════════════════════════

### Option A — DB Browser for SQLite (GUI, recommended)
Download free → https://sqlitebrowser.org/dl/

1. Open DB Browser → **Open Database**
2. Navigate to your project folder → select `raftaar.db`
3. Click **Browse Data** tab → select a table

Run these queries under the **Execute SQL** tab:

---

### DB TEST 1 — Check all tables exist
```sql
SELECT name FROM sqlite_master
WHERE type = 'table'
ORDER BY name;
```
**Expected output:**
```
scores
sessions
users
```

---

### DB TEST 2 — Check indexes exist
```sql
SELECT name, tbl_name FROM sqlite_master
WHERE type = 'index'
ORDER BY tbl_name;
```
**Expected output:**
```
idx_scores_played   scores
idx_scores_score    scores
idx_scores_user     scores
```

---

### DB TEST 3 — Check password is hashed (NOT plain text)
```sql
SELECT username, password_hash FROM users;
```
**Expected — hash starts with `pbkdf2:sha256`:**
```
TestPlayer1 | pbkdf2:sha256:600000$xK3m...
```
**If you see `Test123` in plain text → hashing is broken.**

---

### DB TEST 4 — Count users, scores, sessions
```sql
SELECT
  (SELECT COUNT(*) FROM users)    AS total_users,
  (SELECT COUNT(*) FROM scores)   AS total_scores,
  (SELECT COUNT(*) FROM sessions) AS active_sessions;
```

---

### DB TEST 5 — Verify scores saved correctly
```sql
SELECT u.username, s.score, s.coins, s.level, s.played_at
FROM scores s
JOIN users u ON s.user_id = u.id
ORDER BY s.score DESC;
```

---

### DB TEST 6 — Check session expiry is set correctly
```sql
SELECT token, username, expires_at,
  CASE WHEN expires_at > datetime('now') THEN 'ACTIVE' ELSE 'EXPIRED' END AS status
FROM sessions;
```
**Expected:** All recent sessions show `ACTIVE`

---

### DB TEST 7 — Simulate leaderboard query (same as the API uses)
```sql
SELECT u.username,
       MAX(s.score)  AS best_score,
       COUNT(s.id)   AS games_played,
       MAX(s.level)  AS max_level
FROM scores s
JOIN users u ON s.user_id = u.id
GROUP BY s.user_id
ORDER BY best_score DESC
LIMIT 10;
```

---

### DB TEST 8 — Check expired sessions get cleaned up
After running the purge manually:
```sql
-- First: insert a fake expired session to test cleanup
INSERT INTO sessions (token, user_id, username, expires_at)
VALUES ('test_expired_token', 1, 'TestPlayer1', '2020-01-01 00:00:00');

-- Verify it exists
SELECT COUNT(*) FROM sessions WHERE token = 'test_expired_token';

-- Now trigger cleanup (same query the app runs)
DELETE FROM sessions WHERE expires_at < datetime('now');

-- Verify it's gone
SELECT COUNT(*) FROM sessions WHERE token = 'test_expired_token';
-- Expected: 0
```

---

### Option B — SQLite via Terminal
```bash
# Open the database
sqlite3 raftaar.db

# Run any query
sqlite> SELECT name FROM sqlite_master WHERE type='table';
sqlite> SELECT username, password_hash FROM users;
sqlite> SELECT * FROM scores ORDER BY score DESC;
sqlite> .quit
```

---

## ═══════════════════════════════════════
## QUICK REFERENCE — All Endpoints
## ═══════════════════════════════════════

| # | Method | Endpoint | Auth | Purpose |
|---|--------|----------|------|---------|
| 1 | POST | `/api/signup` | No | Create account |
| 2 | POST | `/api/login` | No | Login → get token |
| 3 | POST | `/api/logout` | Token | Invalidate session |
| 4 | GET | `/api/me` | Token | My profile + stats |
| 5 | POST | `/api/scores` | Token | Submit game score |
| 6 | GET | `/api/leaderboard?period=` | No | Global leaderboard |
| 7 | GET | `/api/my-scores` | Token | My score history |

**Auth header format:**
```
Authorization: Bearer <your_token_here>
```

---

## TEST CHECKLIST

### API (Postman)
- [ ] Signup creates account and returns token
- [ ] Signup rejects bad passwords (7 cases)
- [ ] Signup rejects duplicate username
- [ ] Login returns token
- [ ] Login rejects wrong password
- [ ] /api/me returns profile (with token)
- [ ] /api/me returns 401 (without token)
- [ ] Score submit works (with token)
- [ ] Score submit rejects invalid score
- [ ] Leaderboard returns sorted results (all 4 periods)
- [ ] My-scores returns history
- [ ] Logout invalidates token
- [ ] Token unusable after logout

### Database (DB Browser / terminal)
- [ ] All 3 tables exist
- [ ] All 3 indexes exist
- [ ] Passwords stored as pbkdf2 hash (not plain text)
- [ ] Scores saved with correct user_id
- [ ] Sessions have valid expiry timestamps
- [ ] Expired session cleanup works
