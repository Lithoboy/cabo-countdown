import requests
import os

def download_image():
    # URL of a beach image from Unsplash
    url = "https://images.unsplash.com/photo-1507525428034-b723cf961d3e"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; CaboCountdownBot/1.0; +https://replit.com/@replit/CaboCountdown)'
    }
    
    try:
        # Ensure the directory exists
        os.makedirs('static/images', exist_ok=True)
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Save the image to the static/images directory
        with open('static/images/cabo-arch.jpg', 'wb') as f:
            f.write(response.content)
        print("Image downloaded successfully!")
        
    except Exception as e:
        print(f"Error downloading image: {e}")

if __name__ == "__main__":
    download_image()
