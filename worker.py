import functools
from flask import Flask
import google.generativeai as genai

from app import create_app
from app.models import Post
from app.cron.handlers import process_videos


def setup_generative_ai(app: Flask) -> None:
    """
    Place generative ai ready partial method in the app config
    that requires just the prompt.
    """
    genai.configure(api_key=app.config["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-pro")

    # create partial function by supplying safety_settings
    generate_content = functools.partial(
        model.generate_content,
        safety_settings={
            "HARM_CATEGORY_HATE_SPEECH": "block_none",
            "HARM_CATEGORY_HARASSMENT": "block_none",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "block_none",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "block_none",
        },
    )

    # place the func object in the app config
    app.config["generate_content"] = generate_content


if __name__ == "__main__":

    app = create_app()
    setup_generative_ai(app)

    with app.app_context():
        process_videos()
        Post.reindex()
