from flask import Flask, render_template, jsonify
from datetime import datetime
import random

app = Flask(__name__)

# Mock weather data (replace with real API call when API key is available)
def get_weather():
    conditions = ['Sunny', 'Partly Cloudy', 'Clear']
    temps = range(75, 85)
    return {
        'temperature': random.choice(list(temps)),
        'condition': random.choice(conditions),
        'humidity': random.randint(60, 80)
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/weather')
def weather():
    return jsonify(get_weather())
