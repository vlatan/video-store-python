# Factual Docs

[https://factualdocs.com](https://factualdocs.com)

This web app is made using Python (Flask), HTML, CSS, JavaScript, PostgreSQL and Redis. It is basically a documentary library that automatically fetches and posts videos (documentaries) from predetermined sources (YouTube playlists) therefore it heavily utilizes the [YouTube API](https://developers.google.com/youtube/v3/docs).

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

```
docker compose up --build --remove-orphans app
```

Access the app on `https://localhost:5000`


## Run the worker locally

```
docker compose up --build --remove-orphans worker
```

## Run DB migration

1. Set `"python.envFile": ""` in your `.vscode/settings.json` so VS Code doesn't automatically set the environment variables in the virtual environment `.venv` using your `.env` file. Exit all shells and restart VS Code.
2. Make the desired changes to the database models.
3. Comment out the `db.create_all()` in `app/__init__.py` to avoid error due to discrepancy in models that you've just changed and the actual database that is not yet updated.
4. Start the app locally with `docker compose up --build --remove-orphans app`. After it starts you can shut it down with `CTRL+C` after which the database and the redis docker containers will keep running.
5. Change `DB_HOST` and `REDIS_HOST` to `localhost` in the `.env` file so you can run `flask-migrate` CLI commands from your terminal. You can simply comment out the hosts in the `.env` file for this purpose. The `flask-migrate` CLI commands will create an app instance so this instance needs to be able to acces the database and redis on localhost ports to which their docker containers are listening to.
5. If **ONLY** there's no `migrations` folder in the root, run `flask db init`. Then run an inital migration `flask db migrate -m "Initial migration"`. These are one time commands.
6. Run `flask db upgrade` which will create an `alembic_version` table in the database.
7. Switch to remote production database credentials in the `.env` file and run `flask db upgrade` again to apply the upgrade to the production database as well.
8. In future, after every change to the models first save the migration version with `flask db migrate -m "Describe the changes here"` and then run `flask db upgrade` to actually modify the database.
9. Apply `flask db upgrade` again for the production database, after changing the db credentials in the `.env` file, to modify the production database as well.
10. Uncomment `db.create_all()` and restore `DB_HOST` and `REDIS_HOST` to their values.

## License

[![License: GNU GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg?label=License)](/LICENSE "License: GNU GPLv3")