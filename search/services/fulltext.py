"""Provides access to fulltext content for arXiv papers.

**This is currently not in use. Currently arxiv-search does not
index the full text of articles.**

"""

import json
from http import HTTPStatus
from functools import wraps
from urllib.parse import urljoin

import requests

from search.domain import Fulltext
from search.context import get_application_config, get_application_global


class FulltextSession(object):
    """An HTTP session with the fulltext endpoint."""

    def __init__(self, endpoint: str) -> None:
        """Initialize an HTTP session."""
        self._session = requests.Session()
        self._adapter = requests.adapters.HTTPAdapter(max_retries=2)
        self._session.mount("https://", self._adapter)

        if not endpoint[-1] == "/":
            endpoint += "/"
        self.endpoint = endpoint

    def retrieve(self, document_id: str) -> Fulltext:
        """
        Retrieve fulltext content for an arXiv paper.

        Parameters
        ----------
        document_id : str
            arXiv identifier, including version tag. E.g. ``"1234.56787v3"``.
        endpoint : str
            Base URL for fulltext endpoint.

        Returns
        -------
        :class:`.Fulltext`
            Includes the content itself, creation (extraction) date, and
            extractor version.

        Raises
        ------
        ValueError
            Raised when ``document_id`` is not a valid arXiv paper identifier.
        IOError
            Raised when unable to retrieve fulltext content.
        """
        if not document_id:  # This could use further elaboration.
            raise ValueError("Invalid value for document_id")

        try:
            response = requests.get(urljoin(self.endpoint, document_id))
        except requests.exceptions.SSLError as ex:
            raise IOError("SSL failed: %s" % ex)

        if response.status_code != HTTPStatus.OK:
            raise IOError(
                "%s: could not retrieve fulltext: %i"
                % (document_id, response.status_code)
            )
        try:
            data = response.json()
        except json.decoder.JSONDecodeError as ex:
            raise IOError(
                "%s: could not decode response: %s" % (document_id, ex)
            ) from ex
        return Fulltext(**data)  # type: ignore
        # See https://github.com/python/mypy/issues/3937


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault(
        "FULLTEXT_ENDPOINT", "https://fulltext.arxiv.org/fulltext/"
    )


def get_session(app: object = None) -> FulltextSession:
    """Get a new session with the fulltext endpoint."""
    config = get_application_config(app)
    endpoint = config.get(
        "FULLTEXT_ENDPOINT", "https://fulltext.arxiv.org/fulltext/"
    )
    return FulltextSession(endpoint)


def current_session() -> FulltextSession:
    """Get/create :class:`.FulltextSession` for this context."""
    g = get_application_global()
    if not g:
        return get_session()
    if "fulltext" not in g:
        g.fulltext = get_session()  # type: ignore
    return g.fulltext  # type: ignore


@wraps(FulltextSession.retrieve)
def retrieve(document_id: str) -> Fulltext:
    """Retrieve an arxiv document by id."""
    return current_session().retrieve(document_id)
