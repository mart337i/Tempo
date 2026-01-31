# Standard library imports
import os
import importlib
import string

# Third-party imports
from fastapi import Depends, FastAPI, APIRouter
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
import uvicorn

import logging
_logger = logging.getLogger(__name__)

# Miscellaneous
import urllib3

# Disable SSL warnings
urllib3.disable_warnings()

class FastAPI(FastAPI):
    def __init__(
            self,
            **kwargs
        ):
        
        # Run Base class init
        super().__init__(
            title=kwargs.get('name', 'Tempo API'),
            openapi_url=kwargs.get('openapi_url', '/openapi.json'),
            docs_url=kwargs.get('docs_url', '/docs'),
            description=kwargs.get('description', 'Tempo API'),
            version=kwargs.get('version', '0.1.0'),
            license_info=kwargs.get('license_info', {
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
            }),
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
            Import all routes using dynamic importing
        """
        ...

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
        route_prefix = set()
        for route in self.routes:
            if isinstance(route, APIRoute):
                if route.name in route_names:
                    raise Exception(f"Route function names {[route.name]} should be unique")
                if route.path in route_prefix:
                    raise Exception(f"Route prefix {[route.path]} should be unique")
                route.operation_id = route.name
                route_names.add(route.name)
                route_prefix.add(route.path)

    def include_router_from_module(self, module_name: str):
        """
        Import module and check if it contains 'router' attribute.
        if it does include the route in the fastapi app 
        """
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, 'router'):
                if not isinstance(module.router, APIRouter):
                    print(isinstance(module.router, APIRoute))
                    _logger.debug(f"Failed to registre router from module: {module_name}")
                    return

                self.include_router(
                    router=module.router,
                )

                _logger.debug(f"Registered router from module: {module_name}")
        except ModuleNotFoundError as e:
            _logger.error(f"Module not found: {module_name}, error: {e}")
        except AttributeError as e:
            _logger.error(f"Module '{module_name}' does not have 'router' attribute, error: {e}")
        except Exception as e:
            _logger.error(f"Module '{module_name}' failed with the following error: {e}")

    def start(self, **kwargs):
        # Start the server with uvicorn
        uvicorn.run(
            app=f"tempo.fastapi:create_api",
            host=kwargs.get("host"),
            port=kwargs.get("port"),
            reload=True,
            workers=kwargs.get("workers"),
            timeout_keep_alive=30,
            log_config=None,
            access_log=None,
            factory=True
        )

def create_api(kwargs) -> FastAPI:
    api = FastAPI(
        **values
    )

    api.configure()

    return api