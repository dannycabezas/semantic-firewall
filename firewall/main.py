import uvicorn
from fastapi import FastAPI

from container import FirewallContainer
from semantic_firewall import app as semantic_app  # Existing routers/endpoints
from core.bootstrap import register_startup_events


def create_app(container: FirewallContainer) -> FastAPI:
    """
    Create FastAPI instance and register routers/events.

    For now we reuse the app already defined in `semantic_firewall.py`
    to avoid breaking the behavior while the refactor is completed.
    Later, the routers will be extracted and explicitly included here.
    """
    # For now we simply reuse the existing app,
    # but register the bootstrap hooks (startup, etc.).
    register_startup_events(semantic_app)
    return semantic_app


def create_application() -> tuple[FastAPI, object]:
    """
    Create the FastAPI application and the associated configuration.

    Returns:
        Tuple containing the FastAPI application and the configuration
    """
    container = FirewallContainer()
    app = create_app(container)

    # For now we use directly the config from the container; later it can be wrapped in a more explicit configuration provider.
    app_config = container.config()
    return app, app_config


app, app_config = create_application()


def run_application() -> None:
    """Run the FastAPI application with uvicorn."""
    host = getattr(app_config.server, "host", "0.0.0.0")
    port = getattr(app_config.server, "port", 8000)
    log_level = getattr(app_config, "log_level", "info")
    environment = getattr(app_config, "environment", "development")

    uvicorn.run(
        "firewall.main:app",
        host=host,
        port=port,
        log_level=str(log_level).lower(),
        access_log=str(environment).lower() == "development",
        reload=str(environment).lower() == "development",
    )


if __name__ == "__main__":
    run_application()


