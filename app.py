from flask import Flask, jsonify
from flask_cors import CORS
from stock_picker import run_picker
import threading
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

tasks = {}

def run_task(task_id, max_results=5):
    def progress_callback(progress_info):
        tasks[task_id]['progress'] = progress_info
        tasks[task_id]['updated_at'] = datetime.now().isoformat()
        if progress_info.get('status') == 'completed':
            tasks[task_id]['completed'] = True
            tasks[task_id]['result'] = progress_info.get('result')
        elif progress_info.get('status') == 'error':
            tasks[task_id]['completed'] = True
            tasks[task_id]['error'] = progress_info.get('message')
    
    run_picker(max_results=max_results, progress_callback=progress_callback)

@app.route('/pick', methods=['GET'])
def pick_stocks():
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        'task_id': task_id,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'progress': {'status': 'pending', 'message': '任务已创建'},
        'completed': False
    }
    
    thread = threading.Thread(target=run_task, args=(task_id, 5))
    thread.start()
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': '选股任务已开始，请使用 /progress/<task_id> 查询进度'
    })

@app.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    if task_id not in tasks:
        return jsonify({
            'success': False,
            'message': '任务不存在'
        }), 404
    
    task = tasks[task_id]
    return jsonify({
        'success': True,
        'task': task
    })

@app.route('/tasks', methods=['GET'])
def list_tasks():
    return jsonify({
        'success': True,
        'tasks': list(tasks.keys())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
