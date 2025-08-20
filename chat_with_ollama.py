import requests
import json

# Working endpoint configuration
BASE_URL = "https://mepa.monolithicpower.com"
API_KEY = "sk-1433c71bc11d4cc68582547caf5c064d"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def list_models():
    """List all available models"""
    url = f"{BASE_URL}/ollama/api/tags"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        models = response.json()
        print("Available models:")
        for model in models.get('models', []):
            print(f"  - {model['name']} ({model['details']['parameter_size']})")
        return models['models']
    else:
        print(f"Error listing models: {response.status_code} - {response.text}")
        return []

def generate_response(model_name, prompt):
    """Generate a response using the specified model"""
    url = f"{BASE_URL}/ollama/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False  # Get complete response at once
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        return result.get('response', 'No response generated')
    else:
        print(f"Error generating response: {response.status_code} - {response.text}")
        return None

def chat(prompt):
    """Chat function using hardcoded qwen2.5:latest model"""
    model_name = "gpt-oss:20b"  # 70.6B parameter model
    return generate_response(model_name, prompt)

# Main execution
if __name__ == "__main__":
    # List available models
    models = list_models()
    
    # Test the chat function with qwen2.5:latest
    print(f"\n--- Testing chat() function with qwen2.5:latest ---")
    test_prompt = "Hello! Can you introduce yourself in one sentence?"
    response = chat(test_prompt)
    
    if response:
        print(f"Prompt: {test_prompt}")
        print(f"Response: {response}")
    else:
        print("Failed to generate response")