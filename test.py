from google import genai

client = genai.Client(api_key="AIzaSyDFiuQ0Uxrf7Zgd-6QXyVEhI0CjU6BwhGg")

for model in client.models.list():
    print(model.name)