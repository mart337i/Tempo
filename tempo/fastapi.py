# Standard library imports
import os
import sys
import importlib
import string
from pathlib import Path

# Third-party imports
from fastapi import Depends, APIRouter
from fastapi import FastAPI as FastAPIBase
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
import uvicorn

import logging

_logger = logging.getLogger(__name__)

# Miscellaneous
import urllib3

# Disable SSL warnings
urllib3.disable_warnings()


class FastAPI(FastAPIBase):
    def __init__(self, **kwargs):
        # Run Base class init
        super().__init__(
            title=kwargs.get("name", "Tempo API"),
            openapi_url=kwargs.get("openapi_url", "/openapi.json"),
            docs_url=kwargs.get("docs_url", "/docs"),
            description=kwargs.get("description", "Tempo API"),
            version=kwargs.get("version", "0.1.0"),
            license_info=kwargs.get(
                "license_info",
                {
                    "name": "Apache 2.0",
                    "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
                },
            ),
        )

    def configure(self):
        """
        Configure the application - only called when server command is executed.
        """
        self.setup_base_routes()
        self.setup_addon_routers()
        self.use_route_names_as_operation_ids()
        self.setup_middleware()
        return self

    def setup_base_routes(self) -> None:
        pass

    def setup_addon_routers(self) -> None:
        """
        Scan the addons/ directory and dynamically register every addon router.

        Convention: each addon is a subdirectory of addons/ that contains a
        router.py exposing a FastAPI APIRouter instance named ``router``.

            addons/
            ├── __init__.py
            ├── users/
            │   ├── __init__.py
            │   └── router.py          # has: router = APIRouter(...)
            └── products/
                ├── __init__.py
                └── router.py

        The addons directory is resolved relative to the project root that is
        already on sys.path (added by tempo/__init__.py).
        """
        # Locate the addons/ directory.  Walk up from this file (tempo/fastapi.py)
        # to the project root, then into addons/.
        project_root = Path(__file__).resolve().parent.parent
        addons_dir = project_root / "addons"

        if not addons_dir.is_dir():
            _logger.debug("No addons/ directory found at %s", addons_dir)
            return

        # Ensure project root is importable (belt-and-suspenders; tempo/__init__.py
        # already does this, but the factory process may not have gone through it).
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # Walk every direct child of addons/; if it looks like a package with a
        # router module, register it.
        for addon_path in sorted(addons_dir.iterdir()):
            if not addon_path.is_dir():
                continue
            # Skip hidden dirs and __pycache__
            if addon_path.name.startswith((".", "_")):
                continue
            # Must have a router.py to be considered an addon
            if not (addon_path / "router.py").is_file():
                _logger.debug("Skipping %s — no router.py found", addon_path.name)
                continue

            module_name = f"addons.{addon_path.name}.router"
            _logger.debug("Loading addon router: %s", module_name)
            self.include_router_from_module(module_name)

    def setup_middleware(self):
        origins = [
            "http://localhost",
            "http://localhost:8000",
            "http://localhost:8080",
        ]

        self.add_middleware(
            middleware_class=CORSMiddleware,
            allow_credentials=True,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # NOTE:: Enable this if it need to be exposed to the WAN
        # self.add_middleware(
        #     # Ensures all trafic to server is ssl encrypted or is rederected to https / wss
        #     middleware_class=HTTPSRedirectMiddleware
        # )

    def use_route_names_as_operation_ids(self) -> None:
        """
        Simplify operation IDs so that generated API clients have simpler function
        names.

        Should be called only after all routes have been added.
        """
        route_names = set()
        route_endpoints = set()  # (path, frozenset(methods)) pairs
        for route in self.routes:
            if isinstance(route, APIRoute):
                if route.name in route_names:
                    raise Exception(
                        f"Route function names {[route.name]} should be unique"
                    )
                endpoint_key = (route.path, frozenset(route.methods or []))
                if endpoint_key in route_endpoints:
                    raise Exception(
                        f"Route {route.path} {route.methods} should be unique"
                    )
                route.operation_id = route.name
                route_names.add(route.name)
                route_endpoints.add(endpoint_key)

    def include_router_from_module(self, module_name: str):
        """
        Import module and check if it contains 'router' attribute.
        if it does include the route in the fastapi app
        """
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "router"):
                if not isinstance(module.router, APIRouter):
                    print(isinstance(module.router, APIRoute))
                    _logger.debug(
                        f"Failed to registre router from module: {module_name}"
                    )
                    return

                self.include_router(
                    router=module.router,
                )

                _logger.debug(f"Registered router from module: {module_name}")
        except ModuleNotFoundError as e:
            _logger.error(f"Module not found: {module_name}, error: {e}")
        except AttributeError as e:
            _logger.error(
                f"Module '{module_name}' does not have 'router' attribute, error: {e}"
            )
        except Exception as e:
            _logger.error(
                f"Module '{module_name}' failed with the following error: {e}"
            )

    def start(self, **kwargs):
        """
        Start the server with uvicorn.

        This method exports configuration to environment variables before
        starting uvicorn, allowing the factory function to read the config.
        """
        from tempo.config import TempoConfig

        # Create config and update with CLI arguments
        config = TempoConfig(config_file=kwargs.get("config"))
        config.update_from_args(kwargs)

        # Export to environment variables for factory communication
        config.export_to_env()

        # Configure logging before uvicorn.run() so startup messages are captured
        from tempo.log import setup_logging

        setup_logging(config)

        # Get server configuration
        server_config = config.get_server_config()

        # Start the server with uvicorn
        uvicorn.run(
            app=f"tempo.fastapi:create_api",
            host=server_config["host"],
            port=server_config["port"],
            reload=server_config["reload"],
            workers=server_config["workers"],
            timeout_keep_alive=30,
            log_config=None,
            factory=True,
        )


def create_api() -> FastAPI:
    """
    Factory function to create the FastAPI application.

    This function is called by uvicorn in factory mode. It reads configuration
    from environment variables that were set by the CLI before starting uvicorn.

    Returns:
        Configured FastAPI application instance
    """
    from tempo.config import TempoConfig

    # Create a fresh config instance to read from environment variables
    # Do NOT use get_config() singleton here because it may have been
    # initialized before environment variables were set
    config = TempoConfig()

    from tempo.log import setup_logging

    setup_logging(config)

    server_config = config.get_server_config()

    # Create FastAPI instance with configuration
    api = FastAPI(
        name=server_config["name"],
        openapi_url=server_config["openapi_url"],
        docs_url=server_config["docs_url"],
        description=server_config["description"],
        version=server_config["version"],
    )

    # Configure routes, middleware, etc.
    api.configure()

    return api
