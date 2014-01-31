from dexter.app import app
from flask.ext.mako import render_template

from dexter.models import Document

import dexter.articles

@app.route('/')
def home():
    documents = Document.query.order_by(Document.published_at.desc()).limit(100)
    return render_template('index.haml',
            documents=documents)
