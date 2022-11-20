from app import create_app

app = create_app()

if __name__ == "__main__":
    ssl_context = ("certs/cert.pem", "certs/key.pem")
    app.run("localhost", ssl_context=ssl_context)
