import requests
import os

def download_images():
    # List of image URLs and their target filenames
    images = [
        ("https://images.unsplash.com/photo-1583037189850-1921ae7c6c22", "el-arco.jpg"),
        ("https://images.unsplash.com/photo-1583037189850-1921ae7c6c22", "medano-beach.jpg"),
        ("https://images.unsplash.com/photo-1596178065887-1198b6148b2b", "water-activities.jpg"),
        ("https://images.unsplash.com/photo-1540541338287-41700207dee6", "sunset-cruise.jpg"),
        ("https://images.unsplash.com/photo-1544551763-46a013bb70d5", "resort-view.jpg"),
        ("https://images.unsplash.com/photo-1560246874-f813c1e47bbe", "snorkeling.jpg")
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; CaboCountdownBot/1.0; +https://replit.com/@replit/CaboCountdown)'
    }
    
    try:
        os.makedirs('static/images', exist_ok=True)
        
        for url, filename in images:
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                with open(f'static/images/{filename}', 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded {filename} successfully!")
            except Exception as e:
                print(f"Error downloading {filename}: {e}")
            
    except Exception as e:
        print(f"Error creating directory: {e}")

if __name__ == "__main__":
    download_images()
