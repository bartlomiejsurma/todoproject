import io
import os
import tempfile
from pathlib import Path

from app.routes import app, db

root = Path(tempfile.mkdtemp())
app.config['UPLOAD_FOLDER'] = str(root / 'gallery')
app.config['ATTACHMENTS_FOLDER'] = str(root / 'attachments')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ATTACHMENTS_FOLDER'], exist_ok=True)

db.DB_FILE = str(root / 'camper.db')
db.init_db()
trip_id = db.add_trip('Test Trip', 'X', '2024-01-01', '2024-01-02', '')

client = app.test_client()
with client.session_transaction() as sess:
    sess['logged_in'] = True

resp = client.post(
    '/podroze',
    data={
        'action': 'upload_image',
        'trip_id': trip_id,
        'trip_image': (io.BytesIO(b'abc123'), 'photo.jpg'),
    },
    content_type='multipart/form-data',
)
print('status', resp.status_code)
files = os.listdir(app.config['UPLOAD_FOLDER'])
print('gallery files', files)
for fname in files:
    path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
    print('exists', os.path.exists(path), 'size', os.path.getsize(path))
    with open(path, 'rb') as fh:
        print('content', fh.read())
    route_resp = client.get('/static/gallery/' + fname)
    print('route', route_resp.status_code, route_resp.headers.get('Content-Type'))
    print(route_resp.data[:50])
