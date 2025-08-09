# modules/history_manager.py
import json, os, threading
from datetime import datetime

LOCK = threading.Lock()

class HistoryManager:
    def __init__(self, path='history.json'):
        self.path = path
        if not os.path.exists(self.path):
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump({'runs': []}, f)

    def append_run(self, summary: dict, details: dict = None):
        with LOCK:
            data = self._read()
            entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'summary': summary,
                'details': details or {}
            }
            data['runs'].append(entry)
            tmp = self.path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)

    def get_last_runs(self, n=3):
        data = self._read()
        return data.get('runs', [])[-n:] if n and data.get('runs') else []

    def _read(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {'runs': []}
