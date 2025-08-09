# modules/logger_module.py
import csv, os, tempfile, shutil
from datetime import datetime

class OutreachLogger:
    def __init__(self, path='outreach_log.csv'):
        self.path = path
        if not os.path.exists(self.path):
            with open(self.path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['timestamp','url','contact','subject','status'])
                writer.writeheader()

    def already_processed(self, url):
        try:
            with open(self.path, newline='', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    if row.get('url') == url:
                        return True
        except FileNotFoundError:
            return False
        return False

    def record(self, url, contact='', subject='', status=''):
        timestamp = datetime.utcnow().isoformat()
        row = {'timestamp': timestamp, 'url': url, 'contact': contact, 'subject': subject, 'status': status}
        fd, tmp = tempfile.mkstemp(prefix='outreach_', suffix='.csv')
        os.close(fd)
        if os.path.exists(self.path):
            shutil.copyfile(self.path, tmp)
        with open(tmp, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp','url','contact','subject','status'])
            writer.writerow(row)
        os.replace(tmp, self.path)
