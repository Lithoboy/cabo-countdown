// Set the date for December 19th of the current year
const targetDate = new Date(new Date().getFullYear(), 11, 19);

// Client-side cache for weather data
const weatherCache = {
    weather: null,
    forecast: null,
    weatherTimestamp: null,
    forecastTimestamp: null
};

// Cache duration in milliseconds
const WEATHER_CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
const FORECAST_CACHE_DURATION = 30 * 60 * 1000; // 30 minutes

// Update intervals
const WEATHER_UPDATE_INTERVAL = 15 * 60 * 1000; // 15 minutes
const FORECAST_UPDATE_INTERVAL = 30 * 60 * 1000; // 30 minutes

function updateCountdown() {
    const currentDate = new Date();
    const difference = targetDate - currentDate;

    const days = Math.floor(difference / (1000 * 60 * 60 * 24));
    const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((difference % (1000 * 60)) / 1000);

    document.getElementById('days').textContent = days.toString().padStart(2, '0');
    document.getElementById('hours').textContent = hours.toString().padStart(2, '0');
    document.getElementById('minutes').textContent = minutes.toString().padStart(2, '0');
    document.getElementById('seconds').textContent = seconds.toString().padStart(2, '0');
}

async function fetchWithRetry(url, retries = 3, initialDelay = 1000) {
    let lastError;
    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Accept': 'application/json',
                    'User-Agent': 'Cabo Countdown App/1.0'
                },
                cache: 'no-cache'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
            }
            
            const data = await response.json();
            if (!data) {
                throw new Error('Empty response received');
            }
            
            return data;
        } catch (error) {
            lastError = error;
            console.warn(`Attempt ${i + 1}/${retries} failed:`, error.message);
            
            if (i < retries - 1) {
                const delay = Math.min(initialDelay * Math.pow(2, i), 8000); // Cap at 8 seconds
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    throw lastError;
}

function isCacheValid(timestamp, duration) {
    return timestamp && (Date.now() - timestamp) < duration;
}

function updateWeatherUI(data, showFallback = false) {
    const tempElement = document.getElementById('temperature');
    const condElement = document.getElementById('condition');
    const humElement = document.getElementById('humidity');

    if (showFallback) {
        tempElement.parentElement.classList.add('text-warning');
        condElement.parentElement.classList.add('text-warning');
    } else {
        tempElement.parentElement.classList.remove('text-warning');
        condElement.parentElement.classList.remove('text-warning');
    }

    tempElement.textContent = data.temperature;
    condElement.textContent = data.condition;
    humElement.textContent = data.humidity;
}

async function updateWeather() {
    try {
        // Check cache first
        if (isCacheValid(weatherCache.weatherTimestamp, WEATHER_CACHE_DURATION)) {
            updateWeatherUI(weatherCache.weather, weatherCache.weather.is_fallback);
            return;
        }

        const data = await fetchWithRetry('/api/weather');
        
        if (!data || (data.temperature === '--' && data.condition === '--')) {
            throw new Error('Invalid weather data received');
        }

        // Update cache
        weatherCache.weather = data;
        weatherCache.weatherTimestamp = Date.now();
        
        updateWeatherUI(data, data.is_fallback);
    } catch (error) {
        console.error('Error fetching weather:', error.message);
        
        // Use cached data if available
        if (weatherCache.weather) {
            updateWeatherUI(weatherCache.weather, true);
        } else {
            // Show error state
            document.getElementById('temperature').textContent = '--';
            document.getElementById('condition').textContent = 'Service Unavailable';
            document.getElementById('humidity').textContent = '--';
            
            document.getElementById('temperature').parentElement.classList.add('text-danger');
            document.getElementById('condition').parentElement.classList.add('text-danger');
        }
    }
}

function updateForecastUI(forecasts, showFallback = false) {
    const forecastContainer = document.getElementById('forecast-info');
    forecastContainer.innerHTML = '';

    if (!forecasts || forecasts.length === 0) {
        forecastContainer.innerHTML = `
            <div class="col text-center">
                <p class="text-muted">Forecast temporarily unavailable</p>
            </div>
        `;
        return;
    }

    forecasts.forEach(forecast => {
        const forecastCol = document.createElement('div');
        forecastCol.className = 'col forecast-item';
        
        if (showFallback) {
            forecastCol.classList.add('text-warning');
        }
        
        forecastCol.innerHTML = `
            <div class="text-center">
                <h5 class="forecast-date">${forecast.date}</h5>
                <p class="forecast-temp mb-1">${forecast.temperature}°F</p>
                <p class="forecast-cond mb-1">${forecast.condition}</p>
                <p class="forecast-hum mb-0">Humidity: ${forecast.humidity}%</p>
            </div>
        `;
        
        forecastContainer.appendChild(forecastCol);
    });
}

async function updateForecast() {
    try {
        // Check cache first
        if (isCacheValid(weatherCache.forecastTimestamp, FORECAST_CACHE_DURATION)) {
            updateForecastUI(weatherCache.forecast, false);
            return;
        }

        const forecasts = await fetchWithRetry('/api/forecast');
        
        if (!forecasts || !Array.isArray(forecasts)) {
            throw new Error('Invalid forecast data received');
        }

        // Update cache
        weatherCache.forecast = forecasts;
        weatherCache.forecastTimestamp = Date.now();
        
        updateForecastUI(forecasts, false);
    } catch (error) {
        console.error('Error fetching forecast:', error.message);
        
        // Use cached data if available
        if (weatherCache.forecast) {
            updateForecastUI(weatherCache.forecast, true);
        } else {
            updateForecastUI(null);
        }
    }
}

// Gallery Enhancement Functions
function initializeGallery() {
    const galleryCards = document.querySelectorAll('.gallery-card');
    
    galleryCards.forEach(card => {
        // Add lazy loading to images
        const img = card.querySelector('.card-img-top');
        if (img) {
            img.loading = 'lazy';
        }

        // Add hover animation class
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-5px)';
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
        });

        // Add focus states for accessibility
        const link = card.querySelector('a');
        if (link) {
            link.addEventListener('focus', () => {
                card.style.transform = 'translateY(-5px)';
            });

            link.addEventListener('blur', () => {
                card.style.transform = 'translateY(0)';
            });
        }
    });
}

// Initialize gallery when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeGallery);

// Update countdown every second
setInterval(updateCountdown, 1000);

// Update weather and forecast at different intervals
setInterval(updateWeather, WEATHER_UPDATE_INTERVAL);
setInterval(updateForecast, FORECAST_UPDATE_INTERVAL);

// Initial updates
updateCountdown();
updateWeather().catch(console.error);
updateForecast().catch(console.error);
