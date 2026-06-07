import google.genai as genai

client = genai.Client(
    vertexai=True,
    project="nerve-agent-496707",
    location="us-central1"
)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Say hello!"
)
print(response.text)