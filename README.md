# Doxder

### Description:

This is a web app made in Flask, HTML, CSS, JavaScript and SQLite. It is basically a documentary library that automatically fetches and posts videos (documentaries) from predetermined sources (YouTube playlists) therefore it heavily utilizes the [YouTube API](https://developers.google.com/youtube/v3/docs).

It has multiple criteria for validating the videos such as:

- not already posted
- 30+ minutes in length
- must be public
- not age restricted
- not region restricted
- embeddable and
- audio and title/description must be in English

This info for every video is available at the YouTube API, so once the video satisfies this criteria it is validated and ready to be posted.

The admin can add sources (playlists) to the database. Via cron a Flask view is hit with a POST request several times a day which activates a function in a thread which goes through the playlists in the database and checks if there are new videos by using the YouTube API and automatically posts the videos if any. The app is self-sufficient in that regard. The admin can also post single videos which are automatically checked if they belong to a playlist. If yes that relationship is added to the database.

Users can login using Google. The app doesn't store passwords, just users' Google openid, name and email, so naturally the app makes use of the [Google's OAuth 2.0](https://developers.google.com/identity/protocols/oauth2). For accessing both the YouTube API and the OAuth 2.0 the app uses the [Google API Python client library](https://github.com/googleapis/google-api-python-client).

The app is structured in such a way that Flask is used as an [Application Factory](https://flask.palletsprojects.com/en/2.0.x/patterns/appfactories/) and it is modularized with [blueprints](https://flask.palletsprojects.com/en/2.0.x/blueprints/) such as:

- main (dealing with the homepage and other generic pages)
- posts (for the actual posts/documentaries)
- users (for managing the users and their login logic) and
- errors (for showing custom errors on the front-end)