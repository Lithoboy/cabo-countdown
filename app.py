from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import requests
import os

app = Flask(__name__)

API_KEY = os.environ.get('OPENWEATHERMAP_API_KEY')
BASE_URL = "http://api.openweathermap.org/data/2.5"

def get_current_weather():
    try:
        response = requests.get(
            f"{BASE_URL}/weather",
            params={
                'q': 'Cabo San Lucas,MX',
                'appid': API_KEY,
                'units': 'imperial'
            }
        )
        response.raise_for_status()
        data = response.json()
        return {
            'temperature': round(data['main']['temp']),
            'condition': data['weather'][0]['main'],
            'humidity': data['main']['humidity']
        }
    except Exception as e:
        print(f"Error fetching current weather: {e}")
        return {'temperature': '--', 'condition': '--', 'humidity': '--'}

def get_trip_forecast():
    try:
        response = requests.get(
            f"{BASE_URL}/forecast",
            params={
                'q': 'Cabo San Lucas,MX',
                'appid': API_KEY,
                'units': 'imperial'
            }
        )
        response.raise_for_status()
        data = response.json()
        
        forecasts = []
        used_dates = set()
        
        for item in data['list']:
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
        
        return forecasts
    except Exception as e:
        print(f"Error fetching forecast: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/weather')
def weather():
    return jsonify(get_current_weather())

@app.route('/api/forecast')
def forecast():
    return jsonify(get_trip_forecast())
