
"""
Module for translating classic API `Phrase` objects to the
Elasticsearch DSL and retrieving results.
"""

from typing import Dict, Callable

from elasticsearch_dsl import Q, Search
from elasticsearch_dsl.query import QueryString

from ...domain import ClassicAPIQuery, Phrase, Term, Expression, Field, Operator
from .prepare import SEARCH_FIELDS

def classic_search(search: Search, query: ClassicAPIQuery) -> Search:
    """
    Prepare a :class:`.Search` from a :class:`.ClassicAPIQuery`.

    Parameters
    ----------
    search : :class:`.Search`
        An Elasticsearch search in preparation.
    query : :class:`.ClassicAPIQuery`
        An query originating from the Classic API.

    Returns
    -------
    :class:`.Search`
        The passed ES search object, updated with specific query parameters
        that implement the advanced query.

    """
    dsl_query = _phrase_to_query(query.phrase)

    return search.query(dsl_query)


def _phrase_to_query(phrase: Phrase) -> Q:
    """
    Parses a Phrase of a Classic API request into an ES Q object.
    """
    # base case - simple term query automatically handled by delegation.
    if isinstance(phrase[0], Field) and len(phrase) == 2:
        return _term_to_query(phrase) # type: ignore

    # parse Phrase object an build Q
    q = Q()
    current_operator: Operator = Operator.AND

    for token in phrase:
        if isinstance(token, Operator):
            current_operator = token
        elif isinstance(token, tuple):
            phrase_q: Q = Q()
            if isinstance(token[0], Operator) or len(token) == 3:
                phrase_q = _phrase_to_query(token) # type: ignore
            elif len(token) == 2:
                phrase_q = _term_to_query(token) # type: ignore
            else:
                raise ValueError(f"invalid phrase component: {token}")

            if current_operator is Operator.AND:
                q &= phrase_q
            elif current_operator is Operator.OR:
                q |= phrase_q
            elif current_operator is Operator.ANDNOT:
                q &= ~phrase_q

    return q


def _term_to_query(term: Term) -> Q:
    """
    Parses a fielded term using transfromations from the current API.

    See also: :module:`.api`
    """
    field, val = term
   
    FIELD_TERM_MAPPING: Dict[Field, Callable[[str], Q]] = {
        Field.Author : SEARCH_FIELDS['author'],
        Field.Comment : SEARCH_FIELDS['comments'],
        Field.Identifier : SEARCH_FIELDS['paper_id'], # TODO: edge case of versioned data
        Field.JournalReference : SEARCH_FIELDS['journal_ref'],
        Field.ReportNumber : SEARCH_FIELDS['report_num'],
        Field.SubjectCategory : SEARCH_FIELDS['cross_list_category'], # TODO: unsure of where classifications are unified
        Field.Title : SEARCH_FIELDS['title'],
        Field.All : SEARCH_FIELDS['all']
    }

    return FIELD_TERM_MAPPING[field](val)

