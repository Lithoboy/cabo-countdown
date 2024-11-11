from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import requests
import os
import logging
import time
import json

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
BASE_URL = "https://api.openweathermap.org/data/2.5"

# Common headers for API requests
API_HEADERS = {
    'User-Agent': 'Cabo Countdown App/1.0',
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip, deflate'
}

def make_request_with_retry(url, params, max_retries=3):
    """Make HTTP request with exponential backoff retry logic"""
    last_error = None
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

def get_current_weather():
    try:
        if not API_KEY:
            logger.error("OpenWeatherMap API key is not set!")
            return {'temperature': '--', 'condition': 'API Key Missing', 'humidity': '--'}

        data = make_request_with_retry(
            f"{BASE_URL}/weather",
            params={
                'q': 'Cabo San Lucas,MX',
                'appid': API_KEY,
                'units': 'imperial'
            }
        )
        
        if 'main' not in data or 'weather' not in data or not data['weather']:
            raise ValueError("Invalid weather data structure received")
            
        return {
            'temperature': round(data['main']['temp']),
            'condition': data['weather'][0]['main'],
            'humidity': data['main']['humidity']
        }
    except (requests.Timeout, requests.RequestException) as e:
        logger.error(f"API error in get_current_weather: {str(e)}")
        return {'temperature': '--', 'condition': 'Service Unavailable', 'humidity': '--'}
    except Exception as e:
        logger.error(f"Unexpected error in get_current_weather: {str(e)}")
        return {'temperature': '--', 'condition': 'Service Error', 'humidity': '--'}

def get_trip_forecast():
    try:
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
        
        if 'list' not in data:
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
                        'humidity': item['main']['humidity']
                    })
                    if len(forecasts) >= 5:  # Get up to 5 days
                        break
            except (KeyError, IndexError) as e:
                logger.warning(f"Skipping malformed forecast item: {str(e)}")
                continue
                
        return forecasts
    except (requests.Timeout, requests.RequestException) as e:
        logger.error(f"API error in get_trip_forecast: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in get_trip_forecast: {str(e)}")
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

        # Make a test API call
        data = make_request_with_retry(
            f"{BASE_URL}/weather",
            params={
                'q': 'Cabo San Lucas,MX',
                'appid': API_KEY,
                'units': 'imperial'
            }
        )

        return jsonify({
            'status': 'healthy',
            'message': 'Application is running normally',
            'api_status': 'connected',
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
    return jsonify(get_current_weather())

@app.route('/api/forecast')
def forecast():
    return jsonify(get_trip_forecast())

if __name__ == "__main__":
    # Verify API key is present
    if not API_KEY:
        logger.error("OpenWeatherMap API key is not set!")
    app.run(host="0.0.0.0", port=5000)
