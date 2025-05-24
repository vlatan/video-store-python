"""
Google Generative AI Resources
https://ai.google.dev/tutorials/python_quickstart
https://ai.google.dev/gemini-api/docs/models/gemini
https://github.com/googleapis/python-genai
"""

import functools
from flask import Flask

from google import genai
from google.genai import types

from app import create_app
from app.models import Post
from app.cron.handlers import Documentary, process_videos


def setup_generative_ai(app: Flask) -> None:
    """
    Place generative ai ready partial method in the app config
    that requires just the prompt.
    """
    client = genai.Client(api_key=app.config["GEMINI_API_KEY"])

    safety_settings = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ]

    # create partial function by supplying the model and safety_settings
    app.config["generate_content"] = functools.partial(
        client.models.generate_content,
        model=app.config["GEMINI_MODEL"],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Documentary,
            safety_settings=safety_settings,
        ),
    )


if __name__ == "__main__":

    app = create_app()
    setup_generative_ai(app)

    with app.app_context():
        process_videos()
        Post.reindex()
