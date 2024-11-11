from app import app
from waitress import serve
import logging

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('waitress')
    
    # Run with waitress for production
    logger.info("Starting server with waitress...")
    serve(app, host="0.0.0.0", port=5000, threads=4, url_scheme='http')
