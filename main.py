from app import app
from waitress import serve
import logging
import os
import sys
from datetime import datetime

if __name__ == "__main__":
    # Configure logging with more detailed format
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(deployment_status)s] - %(message)s',
        defaults={'deployment_status': 'STARTUP'}
    )
    logger = logging.getLogger('waitress')
    
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    deployment_env = os.environ.get('REPLIT_DEPLOYMENT', 'development')
    
    # Log startup information
    logger.info(
        'Application initialization started',
        extra={
            'deployment_status': 'INIT',
            'environment': deployment_env,
            'python_version': sys.version,
            'start_time': datetime.utcnow().isoformat()
        }
    )
    
    try:
        # Run with waitress for production
        logger.info(
            f"Starting server with waitress on port {port}...",
            extra={'deployment_status': 'STARTING'}
        )
        serve(app, host="0.0.0.0", port=port, threads=4, url_scheme='http')
        
        logger.info(
            'Server started successfully',
            extra={'deployment_status': 'ACTIVE'}
        )
    except Exception as e:
        logger.error(
            f'Failed to start server: {str(e)}',
            extra={'deployment_status': 'ERROR'},
            exc_info=True
        )
        sys.exit(1)
