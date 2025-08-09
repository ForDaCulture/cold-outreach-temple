import csv
import os
class OutreachLogger:
    def __init__(self, filename='outreach_log.csv'):
        self.filename = filename
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['url', 'email'])
    def log(self, url, email):
        with open(self.filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([url, email])
    def is_logged(self, url):
        with open(self.filename, 'r') as f:
            return any(row[0] == url for row in csv.reader(f))
