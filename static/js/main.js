// Set the date for December 19th of the current year
const targetDate = new Date(new Date().getFullYear(), 11, 19);

// Client-side cache for weather data
const weatherCache = {
    weather: null,
    forecast: null,
    weatherTimestamp: null,
    forecastTimestamp: null
};

// Increased cache durations for free tier optimization
const WEATHER_CACHE_DURATION = 60 * 60 * 1000; // 1 hour
const FORECAST_CACHE_DURATION = 4 * 60 * 60 * 1000; // 4 hours

// Update intervals aligned with cache duration
const WEATHER_UPDATE_INTERVAL = 60 * 60 * 1000; // 1 hour
const FORECAST_UPDATE_INTERVAL = 4 * 60 * 60 * 1000; // 4 hours

// Request configuration
const REQUEST_TIMEOUT = 20000; // 20 seconds
const MAX_RETRIES = 5;
const INITIAL_RETRY_DELAY = 2000;

// Enhanced offline fallback data
const OFFLINE_FALLBACK = {
    weather: {
        temperature: 75,
        condition: 'Data Unavailable',
        humidity: 65,
        is_fallback: true,
        last_updated: null
    },
    forecast: [
        {
            date: 'Dec 19',
            temperature: 75,
            condition: 'Typical',
            humidity: 65,
            is_fallback: true
        }
    ]
};

// Error tracking
let consecutiveErrors = 0;
const MAX_CONSECUTIVE_ERRORS = 3;

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

async function fetchWithTimeout(url, options = {}) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    
    const requestStart = Date.now();
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal,
            headers: {
                'Accept': 'application/json',
                'Cache-Control': 'no-cache',
                ...options.headers
            }
        });
        
        clearTimeout(id);
        
        const responseTime = Date.now() - requestStart;
        console.log(`Request to ${url} completed in ${responseTime}ms`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
        }
        
        const data = await response.json();
        if (!data) {
            throw new Error('Empty response received');
        }
        
        return data;
    } catch (error) {
        clearTimeout(id);
        throw error;
    }
}

async function fetchWithRetry(url, retries = MAX_RETRIES, initialDelay = INITIAL_RETRY_DELAY) {
    let lastError;
    let attempts = [];
    
    for (let i = 0; i < retries; i++) {
        try {
            const data = await fetchWithTimeout(url);
            consecutiveErrors = 0; // Reset error counter on success
            return data;
        } catch (error) {
            lastError = error;
            const retryCount = i + 1;
            const isLastAttempt = retryCount === retries;
            
            const errorInfo = {
                attempt: retryCount,
                timestamp: new Date().toISOString(),
                error: error.message || 'Unknown error',
                type: error.name,
                url: url
            };
            
            attempts.push(errorInfo);
            
            console.warn(
                `Attempt ${retryCount}/${retries} failed:`,
                errorInfo
            );
            
            if (!isLastAttempt) {
                const delay = Math.min(initialDelay * Math.pow(2, i), 16000); // Cap at 16 seconds
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    
    consecutiveErrors++;
    
    const error = {
        message: `Failed after ${retries} attempts`,
        lastError: lastError.message,
        attempts: attempts,
        consecutiveErrors,
        timestamp: new Date().toISOString()
    };
    
    console.error('Request failed completely:', error);
    throw error;
}

function isCacheValid(timestamp, duration) {
    return timestamp && (Date.now() - timestamp) < duration;
}

function updateWeatherUI(data, showFallback = false) {
    const tempElement = document.getElementById('temperature');
    const condElement = document.getElementById('condition');
    const humElement = document.getElementById('humidity');
    
    // Reset error states
    document.querySelectorAll('.weather-error').forEach(el => el.classList.remove('weather-error'));
    
    if (showFallback) {
        tempElement.parentElement.classList.add('text-warning');
        condElement.parentElement.classList.add('text-warning');
        humElement.parentElement.classList.add('data-fallback');
    } else {
        tempElement.parentElement.classList.remove('text-warning');
        condElement.parentElement.classList.remove('text-warning');
        humElement.parentElement.classList.remove('data-fallback');
    }
    
    tempElement.textContent = data.temperature;
    condElement.textContent = data.condition;
    humElement.textContent = data.humidity;
    
    if (data.error) {
        const weatherInfo = document.getElementById('weather-info');
        const errorMsg = document.createElement('p');
        errorMsg.className = 'text-danger small mt-2';
        errorMsg.textContent = 'Weather data may be delayed';
        weatherInfo.appendChild(errorMsg);
    }
}

async function updateWeather() {
    try {
        // Check cache first
        if (isCacheValid(weatherCache.weatherTimestamp, WEATHER_CACHE_DURATION)) {
            if (weatherCache.weather) {
                updateWeatherUI(weatherCache.weather, weatherCache.weather.is_fallback);
                return;
            }
        }
        
        const data = await fetchWithRetry('/api/weather');
        
        if (!data || (data.temperature === undefined && data.condition === undefined)) {
            throw new Error('Invalid weather data received');
        }
        
        // Update cache
        weatherCache.weather = data;
        weatherCache.weatherTimestamp = Date.now();
        
        updateWeatherUI(data, data.is_fallback);
    } catch (error) {
        console.error('Error fetching weather:', {
            message: error.message,
            timestamp: new Date().toISOString(),
            details: error.attempts || [],
            consecutiveErrors,
            cache: {
                hasCache: !!weatherCache.weather,
                cacheAge: weatherCache.weatherTimestamp ? 
                    Math.floor((Date.now() - weatherCache.weatherTimestamp) / 1000) : 'N/A'
            }
        });
        
        // Use cached data if available
        if (weatherCache.weather) {
            updateWeatherUI(weatherCache.weather, true);
        } else {
            const tempElement = document.getElementById('temperature');
            const condElement = document.getElementById('condition');
            const humElement = document.getElementById('humidity');
            
            // Use offline fallback if no cached data
            const fallbackData = OFFLINE_FALLBACK.weather;
            updateWeatherUI(fallbackData, true);
        }
        
        // If too many consecutive errors, increase update interval
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
            console.warn(`Too many consecutive errors (${consecutiveErrors}), increasing update interval`);
            return;
        }
    }
}

function updateForecastUI(forecasts, showFallback = false) {
    const forecastContainer = document.getElementById('forecast-info');
    forecastContainer.innerHTML = '';
    
    if (!forecasts || forecasts.length === 0) {
        forecasts = OFFLINE_FALLBACK.forecast;
        showFallback = true;
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
            if (weatherCache.forecast) {
                updateForecastUI(weatherCache.forecast, false);
                return;
            }
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
        console.error('Error fetching forecast:', {
            message: error.message,
            timestamp: new Date().toISOString(),
            details: error.attempts || [],
            consecutiveErrors,
            cache: {
                hasCache: !!weatherCache.forecast,
                cacheAge: weatherCache.forecastTimestamp ? 
                    Math.floor((Date.now() - weatherCache.forecastTimestamp) / 1000) : 'N/A'
            }
        });
        
        if (weatherCache.forecast) {
            updateForecastUI(weatherCache.forecast, true);
        } else {
            updateForecastUI(null);
        }
        
        // If too many consecutive errors, increase update interval
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
            console.warn(`Too many consecutive errors (${consecutiveErrors}), increasing update interval`);
            return;
        }
    }
}

// Initialize countdown
updateCountdown();
setInterval(updateCountdown, 1000);

// Initialize weather updates with error handling
const initializeWeatherUpdates = async () => {
    try {
        await updateWeather();
        setInterval(updateWeather, WEATHER_UPDATE_INTERVAL);
    } catch (error) {
        console.error('Failed to initialize weather updates:', error);
        setTimeout(initializeWeatherUpdates, 60000); // Retry after 1 minute
    }
};

const initializeForecastUpdates = async () => {
    try {
        await updateForecast();
        setInterval(updateForecast, FORECAST_UPDATE_INTERVAL);
    } catch (error) {
        console.error('Failed to initialize forecast updates:', error);
        setTimeout(initializeForecastUpdates, 60000); // Retry after 1 minute
    }
};

// Add progressive loading
document.addEventListener('DOMContentLoaded', () => {
    // Load critical content first
    updateCountdown();
    
    // Then load weather data with a slight delay
    setTimeout(() => {
        initializeWeatherUpdates();
    }, 1000);
    
    // Finally load forecast data
    setTimeout(() => {
        initializeForecastUpdates();
    }, 2000);
});

// Initialize offline support with proper error handling
if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
        try {
            const registration = await navigator.serviceWorker.register('/sw.js');
            console.log('ServiceWorker registration successful:', registration);
        } catch (err) {
            console.warn('ServiceWorker registration failed:', err.message);
        }
    });
}