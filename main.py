from app import app
from waitress import serve
import logging
import os
import sys
from datetime import datetime

if __name__ == "__main__":
    # Configure logging with minimized format for faster startup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(deployment_status)s] - %(message)s',
        defaults={'deployment_status': 'STARTUP'}
    )
    logger = logging.getLogger('waitress')
    
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    deployment_env = os.environ.get('REPLIT_DEPLOYMENT', 'development')
    
    # Quick startup logging
    logger.info(
        'Starting',
        extra={
            'deployment_status': 'INIT',
            'env': deployment_env
        }
    )
    
    try:
        # Run with waitress using reduced thread count for free tier
        logger.info(
            f"Binding to port {port}",
            extra={'deployment_status': 'STARTING'}
        )
        serve(app, host="0.0.0.0", port=port, threads=2, url_scheme='http')
        
        logger.info(
            'Ready',
            extra={'deployment_status': 'ACTIVE'}
        )
    except Exception as e:
        logger.error(
            str(e),
            extra={'deployment_status': 'ERROR'},
            exc_info=True
        )
        sys.exit(1)
