// Set the date for December 19th of the current year
const targetDate = new Date(new Date().getFullYear(), 11, 19);

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
                }
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
                const delay = initialDelay * Math.pow(2, i); // Exponential backoff
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    throw lastError;
}

async function updateWeather() {
    try {
        const data = await fetchWithRetry('/api/weather');
        if (data.temperature === '--' || !data.temperature) {
            console.warn('Invalid weather data received:', data);
            return;
        }
        
        document.getElementById('temperature').textContent = data.temperature;
        document.getElementById('condition').textContent = data.condition;
        document.getElementById('humidity').textContent = data.humidity;
    } catch (error) {
        console.error('Error fetching weather:', error.message);
        // Add visual feedback for users
        const tempElement = document.getElementById('temperature');
        const condElement = document.getElementById('condition');
        const humElement = document.getElementById('humidity');
        
        if (!tempElement.textContent || tempElement.textContent === '--') {
            tempElement.textContent = '--';
            condElement.textContent = 'Service Unavailable';
            humElement.textContent = '--';
        }
    }
}

async function updateForecast() {
    try {
        const forecasts = await fetchWithRetry('/api/forecast');
        const forecastContainer = document.getElementById('forecast-info');
        
        if (!forecasts || !Array.isArray(forecasts) || forecasts.length === 0) {
            console.warn('Invalid forecast data received:', forecasts);
            return;
        }
        
        forecastContainer.innerHTML = ''; // Clear existing forecasts

        forecasts.forEach(forecast => {
            const forecastCol = document.createElement('div');
            forecastCol.className = 'col forecast-item';
            
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
    } catch (error) {
        console.error('Error fetching forecast:', error.message);
        // Keep existing forecast data if available, otherwise show error state
        const forecastContainer = document.getElementById('forecast-info');
        if (!forecastContainer.children.length) {
            forecastContainer.innerHTML = `
                <div class="col text-center">
                    <p class="text-muted">Forecast temporarily unavailable</p>
                </div>
            `;
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

// Update weather every 15 minutes
const WEATHER_UPDATE_INTERVAL = 15 * 60 * 1000; // 15 minutes
setInterval(updateWeather, WEATHER_UPDATE_INTERVAL);
setInterval(updateForecast, WEATHER_UPDATE_INTERVAL);

// Initial updates
updateCountdown();
updateWeather().catch(console.error);
updateForecast().catch(console.error);
