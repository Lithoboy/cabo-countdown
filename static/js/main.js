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

function updateWeather() {
    fetch('/api/weather')
        .then(response => response.json())
        .then(data => {
            document.getElementById('temperature').textContent = data.temperature;
            document.getElementById('condition').textContent = data.condition;
            document.getElementById('humidity').textContent = data.humidity;
        })
        .catch(error => console.error('Error fetching weather:', error));
}

function updateForecast() {
    fetch('/api/forecast')
        .then(response => response.json())
        .then(forecasts => {
            const forecastContainer = document.getElementById('forecast-info');
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
        })
        .catch(error => console.error('Error fetching forecast:', error));
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

// Update weather every 5 minutes
setInterval(updateWeather, 300000);
setInterval(updateForecast, 300000);

// Initial updates
updateCountdown();
updateWeather();
updateForecast();
