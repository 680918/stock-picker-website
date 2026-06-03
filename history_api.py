import sqlite3
import json
from datetime import datetime
from flask import Flask, request, jsonify, g
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
DATABASE = 'stock_history.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                stocks TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()

@app.route('/api/history', methods=['GET'])
def get_history():
    db = get_db()
    cursor = db.cursor()

    cursor.execute('''
        SELECT id, strategy, stocks, created_at
        FROM stock_history
        ORDER BY created_at DESC
        LIMIT 20
    ''')

    rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            'id': row['id'],
            'strategy': row['strategy'],
            'time': row['created_at'],
            'stocks': json.loads(row['stocks'])
        })

    return jsonify({'success': True, 'history': result})

@app.route('/api/history', methods=['POST'])
def add_history():
    data = request.get_json()

    if not data or 'strategy' not in data or 'stocks' not in data:
        return jsonify({'success': False, 'message': 'Invalid data'}), 400

    db = get_db()
    cursor = db.cursor()

    stocks_json = json.dumps(data['stocks'][:5], ensure_ascii=False)

    cursor.execute(
        'INSERT INTO stock_history (strategy, stocks) VALUES (?, ?)',
        (data['strategy'], stocks_json)
    )
    history_id = cursor.lastrowid
    db.commit()

    return jsonify({'success': True, 'id': history_id})

@app.route('/api/history/<int:history_id>', methods=['DELETE'])
def delete_history(history_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute('DELETE FROM stock_history WHERE id = ?', (history_id,))
    db.commit()

    return jsonify({'success': True})

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    db = get_db()
    cursor = db.cursor()

    cursor.execute('DELETE FROM stock_history')
    db.commit()

    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)