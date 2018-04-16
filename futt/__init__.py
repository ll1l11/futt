from .client import TestClient
from .wrappers import Response


def create_test_app(app):
    app.response_class = Response
    app.test_client_class = TestClient
    app.testing = True
    return app.test_client(use_cookies=False)
