from flask import Response as Response_
from flask import json
from flask.globals import current_app
from werkzeug.exceptions import BadRequest


class JSONMixin(object):
    """Common mixin for both request and response objects to provide JSON
    parsing capabilities.

    .. versionadded:: 1.0
    """

    _cached_json = (Ellipsis, Ellipsis)

    @property
    def is_json(self):
        """Check if the mimetype indicates JSON data, either
        :mimetype:`application/json` or :mimetype:`application/*+json`.

        .. versionadded:: 0.11
        """
        mt = self.mimetype
        return (
            mt == 'application/json'
            or (mt.startswith('application/')) and mt.endswith('+json')
        )

    @property
    def json(self):
        """This will contain the parsed JSON data if the mimetype indicates
        JSON (:mimetype:`application/json`, see :meth:`is_json`), otherwise it
        will be ``None``.
        """
        return self.get_json()

    def _get_data_for_json(self, cache):
        return self.get_data()

    def get_json(self, force=False, silent=False, cache=True):
        """Parse and return the data as JSON. If the mimetype does not
        indicate JSON (:mimetype:`application/json`, see
        :meth:`is_json`), this returns ``None`` unless ``force`` is
        true. If parsing fails, :meth:`on_json_loading_failed` is called
        and its return value is used as the return value.

        :param force: Ignore the mimetype and always try to parse JSON.
        :param silent: Silence parsing errors and return ``None``
            instead.
        :param cache: Store the parsed JSON to return for subsequent
            calls.
        """
        if cache and self._cached_json[silent] is not Ellipsis:
            return self._cached_json[silent]

        if not (force or self.is_json):
            return None

        data = self._get_data_for_json(cache=cache)

        try:
            rv = json.loads(data)
        except ValueError as e:
            if silent:
                rv = None
                if cache:
                    normal_rv, _ = self._cached_json
                    self._cached_json = (normal_rv, rv)
            else:
                rv = self.on_json_loading_failed(e)
                if cache:
                    _, silent_rv = self._cached_json
                    self._cached_json = (rv, silent_rv)
        else:
            if cache:
                self._cached_json = (rv, rv)

        return rv

    def on_json_loading_failed(self, e):
        """Called if :meth:`get_json` parsing fails and isn't silenced. If
        this method returns a value, it is used as the return value for
        :meth:`get_json`. The default implementation raises a
        :class:`BadRequest` exception.

        .. versionchanged:: 0.10
           Raise a :exc:`BadRequest` error instead of returning an error
           message as JSON. If you want that behavior you can add it by
           subclassing.

        .. versionadded:: 0.8
        """
        if current_app is not None and current_app.debug:
            raise BadRequest('Failed to decode JSON object: {0}'.format(e))

        raise BadRequest()


class Response(Response_, JSONMixin):
    pass
