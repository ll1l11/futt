from flask.json import dumps as json_dumps
from flask.testing import FlaskClient
from werkzeug.test import Client, EnvironBuilder
from werkzeug.urls import url_parse


def make_test_environ_builder(
    app, path='/', base_url=None, subdomain=None, url_scheme=None,
    *args, **kwargs
):
    """Create a :class:`~werkzeug.test.EnvironBuilder`, taking some
    defaults from the application.

    :param app: The Flask application to configure the environment from.
    :param path: URL path being requested.
    :param base_url: Base URL where the app is being served, which
        ``path`` is relative to. If not given, built from
        :data:`PREFERRED_URL_SCHEME`, ``subdomain``,
        :data:`SERVER_NAME`, and :data:`APPLICATION_ROOT`.
    :param subdomain: Subdomain name to append to :data:`SERVER_NAME`.
    :param url_scheme: Scheme to use instead of
        :data:`PREFERRED_URL_SCHEME`.
    :param json: If given, this is serialized as JSON and passed as
        ``data``. Also defaults ``content_type`` to
        ``application/json``.
    :param args: other positional arguments passed to
        :class:`~werkzeug.test.EnvironBuilder`.
    :param kwargs: other keyword arguments passed to
        :class:`~werkzeug.test.EnvironBuilder`.
    """

    assert (
        not (base_url or subdomain or url_scheme)
        or (base_url is not None) != bool(subdomain or url_scheme)
    ), 'Cannot pass "subdomain" or "url_scheme" with "base_url".'

    http_host = app.config.get('SERVER_NAME')
    app_root = app.config.get('APPLICATION_ROOT')

    if base_url is None:
        url = url_parse(path)
        base_url = 'http://%s/' % (url.netloc or http_host or 'localhost')
        if app_root:
            base_url += app_root.lstrip('/')
        if url.netloc:
            path = url.path
            if url.query:
                path += '?' + url.query

    if 'json' in kwargs:
        assert 'data' not in kwargs, (
            "Client cannot provide both 'json' and 'data'."
        )

        # push a context so flask.json can use app's json attributes
        with app.app_context():
            kwargs['data'] = json_dumps(kwargs.pop('json'))

        if 'content_type' not in kwargs:
            kwargs['content_type'] = 'application/json'

    return EnvironBuilder(path, base_url, *args, **kwargs)


class TestClient(FlaskClient):
    def open(self, *args, **kwargs):
        auth_token = getattr(self, 'auth_token', None)
        if auth_token:
            kwargs.setdefault('headers', {})['X-Auth-Token'] = auth_token

        as_tuple = kwargs.pop('as_tuple', False)
        buffered = kwargs.pop('buffered', False)
        follow_redirects = kwargs.pop('follow_redirects', False)

        if (
            not kwargs and len(args) == 1
            and isinstance(args[0], (EnvironBuilder, dict))
        ):
            environ = self.environ_base.copy()

            if isinstance(args[0], EnvironBuilder):
                environ.update(args[0].get_environ())
            else:
                environ.update(args[0])

            environ['flask._preserve_context'] = self.preserve_context
        else:
            kwargs.setdefault('environ_overrides', {})['flask._preserve_context'] = self.preserve_context
            kwargs.setdefault('environ_base', self.environ_base)
            builder = make_test_environ_builder(
                self.application, *args, **kwargs
            )

            try:
                environ = builder.get_environ()
            finally:
                builder.close()

        return Client.open(
            self, environ,
            as_tuple=as_tuple,
            buffered=buffered,
            follow_redirects=follow_redirects
        )

    def login(self, path, username, password):
        rv = self.post(path, json=dict(
            username=username,
            password=password,
        ))
        auth_token = rv.json.get('auth_token')
        assert auth_token
        self.auth_token = auth_token
