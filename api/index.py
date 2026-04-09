import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.main import app
from fastapi.responses import HTMLResponse

@app.get('/', response_class=HTMLResponse)
async def serve_frontend():
    html_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'frontend', 'index.html'
    )
    with open(html_path, 'r') as f:
        return HTMLResponse(content=f.read())
