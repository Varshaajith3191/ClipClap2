import requests

# Hugging Face API endpoint and token
API_URL = "https://api-inference.huggingface.co/models/google/t5-v1_1-base"
headers = {"Authorization": "Bearer your_huggingface_api_token"}  # Replace with your actual token

# Input text to summarize
text = "summarize: " + """
So what's new, Mark? How is your new job going? To be honest, I can't complain...
"""

# Make the API request
response = requests.post(API_URL, headers=headers, json={"inputs": text})

# Parse and print the response
summary = response.json()
if isinstance(summary, list) and "generated_text" in summary[0]:
    print("Generated Summary:\n", summary[0]['generated_text'])
elif "error" in summary:
    print("Error:", summary["error"])
else:
    print("Unexpected response:", summary)
