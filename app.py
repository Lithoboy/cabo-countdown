from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import requests
import os
import logging
import time
import json
from cachetools import TTLCache
from ratelimit import limits, sleep_and_retry
import threading

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s:%(lineno)d'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
BASE_URL = "https://api.openweathermap.org/data/2.5"

# Cache configuration - increased TTL for better reliability
weather_cache = TTLCache(maxsize=100, ttl=1800)  # 30 minutes cache
forecast_cache = TTLCache(maxsize=100, ttl=7200)  # 2 hours cache

# Rate limiting configuration - reduced calls to prevent hitting limits
CALLS = 20
RATE_LIMIT_PERIOD = 60

# Common headers for API requests
API_HEADERS = {
    'User-Agent': 'CaboCountdown/1.0',
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip, deflate'
}

# Fallback data
FALLBACK_WEATHER = {
    'temperature': 75,
    'condition': 'Sunny',
    'humidity': 65,
    'is_fallback': True
}

# Thread lock for rate limiting
api_lock = threading.Lock()

@sleep_and_retry
@limits(calls=CALLS, period=RATE_LIMIT_PERIOD)
def make_request_with_retry(url, params, max_retries=5):
    """Make HTTP request with exponential backoff retry logic and rate limiting"""
    last_error = None
    attempts = []
    
    with api_lock:  # Thread-safe request handling
        for attempt in range(max_retries):
            try:
                logger.info(f"Making request attempt {attempt + 1}/{max_retries} to {url}")
                
                response = requests.get(
                    url,
                    params=params,
                    headers=API_HEADERS,
                    timeout=20  # Increased timeout
                )
                
                # Log response details
                logger.info(f"Response status: {response.status_code}, Content length: {len(response.content)}")
                
                response.raise_for_status()
                
                # Verify we got valid JSON response
                data = response.json()
                if not data:
                    raise ValueError("Empty response received")
                
                logger.info("Request successful")
                return data
                
            except requests.Timeout as e:
                error_info = {
                    'attempt': attempt + 1,
                    'error_type': 'timeout',
                    'message': str(e)
                }
                attempts.append(error_info)
                last_error = f"Timeout on attempt {attempt + 1}/{max_retries}"
                logger.warning(last_error, extra={'error_info': error_info})
            except requests.RequestException as e:
                error_info = {
                    'attempt': attempt + 1,
                    'error_type': 'request_error',
                    'message': str(e),
                    'status_code': getattr(e.response, 'status_code', None)
                }
                attempts.append(error_info)
                last_error = f"Request failed on attempt {attempt + 1}/{max_retries}: {str(e)}"
                logger.warning(last_error, extra={'error_info': error_info})
            except (ValueError, json.JSONDecodeError) as e:
                error_info = {
                    'attempt': attempt + 1,
                    'error_type': 'json_error',
                    'message': str(e)
                }
                attempts.append(error_info)
                last_error = f"Invalid JSON response on attempt {attempt + 1}/{max_retries}: {str(e)}"
                logger.warning(last_error, extra={'error_info': error_info})
            
            if attempt < max_retries - 1:
                sleep_time = min(2 ** attempt * 2, 16)  # Cap max sleep time at 16 seconds
                logger.info(f"Waiting {sleep_time} seconds before retry")
                time.sleep(sleep_time)
            else:
                logger.error(f"All retries failed: {last_error}", extra={'attempts': attempts})
                raise RuntimeError({
                    'message': f"All retries failed: {last_error}",
                    'attempts': attempts
                })

def get_cached_weather():
    """Get weather data from cache or API with fallback"""
    cache_key = 'cabo_weather'
    try:
        # Try to get from cache first
        if cache_key in weather_cache:
            logger.info("Returning cached weather data")
            return weather_cache[cache_key]

        if not API_KEY:
            logger.error("OpenWeatherMap API key is not set!")
            return {**FALLBACK_WEATHER, 'error': 'API Key Missing'}

        data = make_request_with_retry(
            f"{BASE_URL}/weather",
            params={
                'q': 'Cabo San Lucas,MX',
                'appid': API_KEY,
                'units': 'imperial'
            }
        )
        
        if not isinstance(data, dict) or 'main' not in data or 'weather' not in data or not data['weather']:
            raise ValueError("Invalid weather data structure received")
            
        weather_data = {
            'temperature': round(data['main']['temp']),
            'condition': data['weather'][0]['main'],
            'humidity': data['main']['humidity'],
            'is_fallback': False,
            'last_updated': datetime.utcnow().isoformat()
        }
        
        # Cache the successful response
        weather_cache[cache_key] = weather_data
        logger.info("Successfully fetched and cached new weather data")
        return weather_data

    except Exception as e:
        logger.error(f"Error in get_cached_weather: {str(e)}", exc_info=True)
        # Return fallback data with error information
        return {**FALLBACK_WEATHER, 'error': str(e)}

def get_cached_forecast():
    """Get forecast data from cache or API with fallback"""
    cache_key = 'cabo_forecast'
    try:
        # Try to get from cache first
        if cache_key in forecast_cache:
            logger.info("Returning cached forecast data")
            return forecast_cache[cache_key]

        if not API_KEY:
            logger.error("OpenWeatherMap API key is not set!")
            return []

        data = make_request_with_retry(
            f"{BASE_URL}/forecast",
            params={
                'q': 'Cabo San Lucas,MX',
                'appid': API_KEY,
                'units': 'imperial'
            }
        )
        
        if not isinstance(data, dict) or 'list' not in data:
            raise ValueError("Invalid forecast data structure received")
        
        forecasts = []
        used_dates = set()
        
        for item in data['list']:
            try:
                forecast_time = datetime.fromtimestamp(item['dt'])
                # Only take one forecast per day (at noon)
                if forecast_time.hour == 12 and forecast_time.date() not in used_dates:
                    used_dates.add(forecast_time.date())
                    forecasts.append({
                        'date': forecast_time.strftime('%b %d'),
                        'time': forecast_time.strftime('%I %p'),
                        'temperature': round(item['main']['temp']),
                        'condition': item['weather'][0]['main'],
                        'humidity': item['main']['humidity'],
                        'is_fallback': False
                    })
                    if len(forecasts) >= 5:  # Get up to 5 days
                        break
            except (KeyError, IndexError) as e:
                logger.warning(f"Skipping malformed forecast item: {str(e)}")
                continue
        
        if forecasts:
            # Cache the successful response
            forecast_cache[cache_key] = forecasts
            logger.info("Successfully fetched and cached new forecast data")
            
        return forecasts
    except Exception as e:
        logger.error(f"Error in get_cached_forecast: {str(e)}", exc_info=True)
        # Return empty list for forecast errors
        return []

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Verify API key is present
        if not API_KEY:
            return jsonify({
                'status': 'warning',
                'message': 'Application running but API key is missing',
                'timestamp': datetime.utcnow().isoformat()
            }), 200

        # Check weather data availability
        weather_data = get_cached_weather()
        forecast_data = get_cached_forecast()

        status = 'healthy'
        messages = []

        if weather_data.get('is_fallback', False):
            status = 'degraded'
            messages.append('Using fallback weather data')

        if not forecast_data:
            status = 'degraded'
            messages.append('Forecast data unavailable')

        return jsonify({
            'status': status,
            'message': ' | '.join(messages) if messages else 'Application is running normally',
            'api_status': 'connected' if not weather_data.get('is_fallback') else 'disconnected',
            'cache_status': {
                'weather_cache_size': len(weather_cache),
                'forecast_cache_size': len(forecast_cache),
                'weather_cache_ttl': weather_cache.ttl,
                'forecast_cache_ttl': forecast_cache.ttl
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/weather')
def weather():
    return jsonify(get_cached_weather())

@app.route('/api/forecast')
def forecast():
    return jsonify(get_cached_forecast())

if __name__ == "__main__":
    # Verify API key is present
    if not API_KEY:
        logger.error("OpenWeatherMap API key is not set!")
    app.run(host="0.0.0.0", port=5000)
