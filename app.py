from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import re
import sqlite3
import os
import secrets
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

DB_PATH = os.environ.get('DB_PATH', 'raftaar.db')

# ─── DB INIT ───────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                coins INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                expires_at DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_scores_user ON scores(user_id);
            CREATE INDEX IF NOT EXISTS idx_scores_played ON scores(played_at);
            CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score DESC);
        ''')

init_db()

# ─── HELPERS ───────────────────────────────────────────────────────────────────
# werkzeug uses pbkdf2:sha256 with a random salt by default —
# salted, slow, and safe against brute-force / rainbow tables.
def hash_password(pw):
    return generate_password_hash(pw)           # e.g. "pbkdf2:sha256:600000$..."

def verify_password(pw, stored_hash):
    return check_password_hash(stored_hash, pw) # timing-safe comparison

def purge_expired_sessions(db):
    """Delete expired sessions opportunistically on every login/signup.
    Keeps the table lean without needing a cron job."""
    db.execute('DELETE FROM sessions WHERE expires_at < ?', (datetime.utcnow().isoformat(),))

def create_session(user_id, username):
    token = secrets.token_hex(32)
    expires = (datetime.utcnow() + timedelta(days=30)).isoformat()
    with get_db() as db:
        purge_expired_sessions(db)   # clean house before inserting
        db.execute(
            'INSERT INTO sessions (token, user_id, username, expires_at) VALUES (?, ?, ?, ?)',
            (token, user_id, username, expires)
        )
    return token

def get_user_from_token(token):
    if not token:
        return None
    with get_db() as db:
        row = db.execute(
            'SELECT user_id, username FROM sessions WHERE token=? AND expires_at > ?',
            (token, datetime.utcnow().isoformat())
        ).fetchone()
    return dict(row) if row else None

def require_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = get_user_from_token(token)
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(user, *args, **kwargs)
    return decorated

# ─── AUTH ROUTES ───────────────────────────────────────────────────────────────
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': 'Username must be 3-20 characters'}), 400
    if not username.replace('_','').replace('-','').isalnum():
        return jsonify({'error': 'Username: letters, numbers, _ or - only'}), 400

    # ── Password rules ──────────────────────────────────────
    # min 6 chars | uppercase | lowercase | digit | no spaces | no symbols
    pw_errors = []
    if len(password) < 6:
        pw_errors.append('at least 6 characters')
    if ' ' in password:
        pw_errors.append('no spaces')
    if not re.search(r'[A-Z]', password):
        pw_errors.append('one uppercase letter')
    if not re.search(r'[a-z]', password):
        pw_errors.append('one lowercase letter')
    if not re.search(r'[0-9]', password):
        pw_errors.append('one number')
    if not re.fullmatch(r'[A-Za-z0-9]+', password):
        pw_errors.append('letters and numbers only (no symbols or spaces)')
    if pw_errors:
        return jsonify({'error': 'Password needs: ' + ', '.join(pw_errors)}), 400

    try:
        with get_db() as db:
            db.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, hash_password(password))
            )
            user = db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        token = create_session(user['id'], username)
        return jsonify({'token': token, 'username': username})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already taken'}), 409

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    with get_db() as db:
        # Fetch by username only, then verify hash separately.
        # Never compare hashes in SQL — salted hashes must use check_password_hash().
        user = db.execute(
            'SELECT id, username, password_hash FROM users WHERE username=?',
            (username,)
        ).fetchone()

    # verify_password uses a constant-time comparison to prevent timing attacks
    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid username or password'}), 401

    token = create_session(user['id'], user['username'])
    return jsonify({'token': token, 'username': user['username']})

@app.route('/api/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token:
        with get_db() as db:
            db.execute('DELETE FROM sessions WHERE token=?', (token,))
    return jsonify({'ok': True})

@app.route('/api/me', methods=['GET'])
@require_auth
def me(user):
    with get_db() as db:
        stats = db.execute(
            '''SELECT COUNT(*) as games, MAX(score) as best, SUM(coins) as total_coins
               FROM scores WHERE user_id=?''',
            (user['user_id'],)
        ).fetchone()
    return jsonify({
        'username': user['username'],
        'games': stats['games'],
        'best': stats['best'] or 0,
        'total_coins': stats['total_coins'] or 0,
    })

# ─── SCORE ROUTES ──────────────────────────────────────────────────────────────
@app.route('/api/scores', methods=['POST'])
@require_auth
def submit_score(user):
    data = request.get_json()
    score = int(data.get('score', 0))
    coins = int(data.get('coins', 0))
    level = int(data.get('level', 1))

    if score < 0 or score > 9999999:
        return jsonify({'error': 'Invalid score'}), 400

    with get_db() as db:
        db.execute(
            'INSERT INTO scores (user_id, score, coins, level) VALUES (?, ?, ?, ?)',
            (user['user_id'], score, coins, level)
        )
    return jsonify({'ok': True})

@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    period = request.args.get('period', 'all')  # daily | weekly | monthly | all

    now = datetime.utcnow()
    if period == 'daily':
        since = (now - timedelta(days=1)).isoformat()
    elif period == 'weekly':
        since = (now - timedelta(weeks=1)).isoformat()
    elif period == 'monthly':
        since = (now - timedelta(days=30)).isoformat()
    else:
        since = '2000-01-01'

    with get_db() as db:
        rows = db.execute(
            '''SELECT u.username, MAX(s.score) as best_score,
                      COUNT(s.id) as games_played,
                      MAX(s.level) as max_level
               FROM scores s
               JOIN users u ON s.user_id = u.id
               WHERE s.played_at >= ?
               GROUP BY s.user_id
               ORDER BY best_score DESC
               LIMIT 50''',
            (since,)
        ).fetchall()

    return jsonify([dict(r) for r in rows])

@app.route('/api/my-scores', methods=['GET'])
@require_auth
def my_scores(user):
    with get_db() as db:
        rows = db.execute(
            '''SELECT score, coins, level, played_at
               FROM scores WHERE user_id=?
               ORDER BY played_at DESC LIMIT 20''',
            (user['user_id'],)
        ).fetchall()
    return jsonify([dict(r) for r in rows])

# ─── SERVE GAME ────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/game')
def game():
    return render_template('game.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
