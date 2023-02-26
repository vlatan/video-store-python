from app import create_app

app = create_app()

if __name__ == "__main__":
    host, port = app.config["HOST"], app.config["PORT"]
    ssl_context = ("certs/cert.pem", "certs/key.pem")
    app.run(host=host, port=port, ssl_context=ssl_context)
