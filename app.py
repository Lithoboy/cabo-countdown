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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
BASE_URL = "https://api.openweathermap.org/data/2.5"

# Cache configuration
weather_cache = TTLCache(maxsize=100, ttl=300)  # 5 minutes cache
forecast_cache = TTLCache(maxsize=100, ttl=1800)  # 30 minutes cache

# Rate limiting configuration - 60 calls per minute
CALLS = 60
RATE_LIMIT_PERIOD = 60

# Common headers for API requests
API_HEADERS = {
    'User-Agent': 'Cabo Countdown App/1.0',
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
def make_request_with_retry(url, params, max_retries=3):
    """Make HTTP request with exponential backoff retry logic and rate limiting"""
    last_error = None
    
    with api_lock:  # Thread-safe request handling
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=API_HEADERS,
                    timeout=10
                )
                response.raise_for_status()
                
                # Verify we got valid JSON response
                data = response.json()
                if not data:
                    raise ValueError("Empty response received")
                    
                return data
                
            except requests.Timeout as e:
                last_error = f"Timeout on attempt {attempt + 1}/{max_retries}"
                logger.warning(last_error)
            except requests.RequestException as e:
                last_error = f"Request failed on attempt {attempt + 1}/{max_retries}: {str(e)}"
                logger.warning(last_error)
            except (ValueError, json.JSONDecodeError) as e:
                last_error = f"Invalid JSON response on attempt {attempt + 1}/{max_retries}: {str(e)}"
                logger.warning(last_error)
            
            if attempt < max_retries - 1:
                sleep_time = min(2 ** attempt, 8)  # Cap max sleep time at 8 seconds
                time.sleep(sleep_time)
            else:
                raise RuntimeError(f"All retries failed: {last_error}")

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
        return weather_data

    except Exception as e:
        logger.error(f"Error in get_cached_weather: {str(e)}")
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
            
        return forecasts
    except Exception as e:
        logger.error(f"Error in get_cached_forecast: {str(e)}")
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
                'forecast_cache_size': len(forecast_cache)
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
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
