import requests
import json

def test_api():
    base_url = "http://127.0.0.1:8080"
    
    # Test health endpoint
    try:
        print("Testing health endpoint...")
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
    except Exception as e:
        print(f"Health endpoint error: {e}")
        print()
    
    # Test the test endpoint
    try:
        print("Testing test endpoint...")
        response = requests.post(f"{base_url}/test")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
    except Exception as e:
        print(f"Test endpoint error: {e}")
        print()
    
    # Test insights endpoint with a simple store
    try:
        print("Testing insights endpoint...")
        data = {"website_url": "https://www.allbirds.com"}
        response = requests.post(
            f"{base_url}/insights", 
            json=data,
            timeout=30
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}...")  # First 500 characters
        print()
    except Exception as e:
        print(f"Insights endpoint error: {e}")
        print()

if __name__ == "__main__":
    test_api()
