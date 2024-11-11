from app import app
from waitress import serve
import logging
import os

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('waitress')
    
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run with waitress for production
    logger.info(f"Starting server with waitress on port {port}...")
    serve(app, host="0.0.0.0", port=port, threads=4, url_scheme='http')
