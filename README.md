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

To run the app in `DEBUG` mode make sure to set the `CONFIG_TYPE=config.DevConfig` in the `.env` file.

Build and bring up all the docker services in the background. The app will be among them.
``` docker
docker compose up --build --remove-orphans -d
```

Observe just the app logs.
``` docker
docker compose logs -f app
```

You can run the app individually with `docker compose run`. The port mapping needs to be specified though. Use the port mapping defined in `compose.yaml` by using `--service-ports`.

``` docker
docker compose run --rm --service-ports app
```

Access the app on `https://localhost:port` where `port` is the port defined in `PORT` in the `.env` file.

If you want to run the app **NOT** in `DEBUG` mode - as if in production - then make sure to set the `CONFIG_TYPE=config.ProdConfig` in the `.env` file.

Run this, but be aware that `gunicorn` will spew **WARNING** in STDOUT that the certificate is unknown because you are using a self-signed certificate.
``` docker
docker compose run --rm --service-ports app \
sh -c 'gunicorn --certfile certs/cert.pem --keyfile certs/key.pem run:app'
```

Access the app on `https://localhost:port` where `port` is the port defined in `PORT` in the `.env` file.


## Run the worker locally

``` docker
docker compose run --rm worker python worker.py
```


## Run DB migration

1. Set `"python.envFile": ""` in your `.vscode/settings.json` so VS Code doesn't automatically set the environment variables in the virtual environment `.venv` using your `.env` file. Exit all shells and restart VS Code.

2. Make the desired changes to the database models.

3. Comment out the `db.create_all()` in `app/__init__.py` to avoid error due to discrepancy in models that you've just changed and the actual database that is not yet updated.

4. Start the app locally with `docker compose up --build --remove-orphans app`. After it starts you can shut it down with `CTRL+C` after which the database and the redis docker containers will keep running.

5. Change `DB_HOST` and `REDIS_HOST` to `localhost` in the `.env` file so you can run flask-migrate CLI commands from your terminal. You can simply comment out the hosts in the `.env` file for this purpose. The flask-migrate CLI commands will create an app instance (which will not be in a docker container) and this instance needs to be able to acces the database and redis on localhost ports to which their docker containers are listening to, given the `EXPOSE_REDIS_PORT` and `EXPOSE_POSTGRES_PORT` env vars are pointing to 6379 and 5432 ports respectively.

6. If **ONLY** there's no `migrations` folder in the root, run `flask db init`. Then run an inital migration `flask db migrate -m "Initial migration"`. These are one time commands.

7. Run `flask db upgrade` which will create an `alembic_version` table in the database and modify the database.

8. If satisfied, switch to remote production database credentials in the `.env` file and run `flask db upgrade` again to apply this upgrade to the production database as well. Keep in mind, you need to push the code changes to production as well. The models are modified so the app needs to know that, not just the database.

9. In future, after every change to the models first save the migration version with `flask db migrate -m "Describe the changes here"` and then run `flask db upgrade` to actually modify the database. Apply `flask db upgrade` again for the production database, after changing the db credentials in the `.env` file, to modify the production database as well.

10. Uncomment `db.create_all()` and restore `DB_HOST` and `REDIS_HOST` to their values.


## License

[![License: GNU GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg?label=License)](/LICENSE "License: GNU GPLv3")