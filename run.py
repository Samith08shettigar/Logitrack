import os
from app import create_app

# Resolve configuration based on environment
config_name = os.environ.get(
    'FLASK_CONFIG', 
    os.environ.get('FLASK_ENV', 'production' if os.environ.get('RENDER') else 'default')
)
app = create_app(config_name)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1']
    app.run(host='0.0.0.0', port=port, debug=debug)

