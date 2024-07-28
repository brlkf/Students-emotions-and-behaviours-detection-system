import os
import google.generativeai as genai

# Replace with your actual API key
api_key = "API Key"

genai.configure(api_key=api_key)


# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
  # safety_settings = Adjust safety settings
  # See https://ai.google.dev/gemini-api/docs/safety-settings
)

def get_gemini_suggestions(emotions, behaviors):
    chat_session = model.start_chat(history=[])
    message = f"Provide suggestions and summarize it for lecturer based on these emotions: {emotions} and behaviors: {behaviors} of all students"
    response = chat_session.send_message(message)
    return {"suggestions": [response.text]}