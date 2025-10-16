import os
from app import create_app

def main():
    """
    Entry point for running the Flask TMF Translation Middleware.

    It creates the Flask application using the factory, reading configuration from environment variables.
    The app listens on the configured SERVICE_PORT (default 3001) and host 0.0.0.0 for containerized environments.
    """
    app = create_app()
    # Ensure port is read from env and default to 3001
    port = int(os.getenv("SERVICE_PORT", "3001"))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
