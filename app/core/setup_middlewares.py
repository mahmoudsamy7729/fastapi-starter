from app.core.middlewares.rate_limit import setup_rate_limit
from slowapi.middleware import SlowAPIMiddleware



def setup_middlewares(app):
    setup_rate_limit(app)
    
    app.add_middleware(SlowAPIMiddleware)