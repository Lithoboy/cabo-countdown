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

// Update countdown every second
setInterval(updateCountdown, 1000);

// Update weather every 5 minutes
setInterval(updateWeather, 300000);

// Initial updates
updateCountdown();
updateWeather();
