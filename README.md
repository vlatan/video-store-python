# Doxder

[https://doxder.com](https://doxder.com)

This web app is made with Flask, HTML, CSS, JavaScript and SQLite. It is basically a documentary library that automatically fetches and posts videos (documentaries) from predetermined sources (YouTube playlists) therefore it heavily utilizes the [YouTube API](https://developers.google.com/youtube/v3/docs).

It validates the videos against multiple criteria such as:

- not already posted
- 30+ minutes in length
- must be public
- not age restricted
- not region restricted
- embeddable
- must have English audio, title and description, and
- it is not an ongoing or scheduled broadcast

Once the video satisfies all of this criteria it is validated and whitelisted to be automatically posted.

Via a background process a function is periodically called which goes through the playlists (video sources) in the database and checks if there are new videos by using the YouTube API and automatically posts the videos if any. The app is autonomous in that regard. The admin can also manually post videos and of course add new video sources (playlists).

Users can login via Google and Facebook. The app doesn't store passwords so naturally it makes use of the [Google's OAuth 2.0](https://developers.google.com/identity/protocols/oauth2) and [Facebook's Login Flow](https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow).

## Run the app locally

Firs build a docker image:
```
docker build . --tag doxder-image
```

Then run a docker container on port 5000:
```
docker run --rm -p 5000:5000 -v .:/app doxder-image python run.py
```

## License

[![License: GNU GPLv3](https://img.shields.io/github/license/vlatan/doxder?label=License)](/LICENSE "License: GNU GPLv3")