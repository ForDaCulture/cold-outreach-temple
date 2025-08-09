import json, os
class HistoryManager:
    def __init__(self, filename='history.json'):
        self.filename = filename
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as f:
                json.dump([], f)
    def save_run(self, lead, pains):
        with open(self.filename, 'r+') as f:
            data = json.load(f)
            data.append({'lead': lead, 'pains': pains})
            f.seek(0)
            json.dump(data, f)
    def get_recent_runs(self, count):
        with open(self.filename, 'r') as f:
            data = json.load(f)
        return data[-count:]
