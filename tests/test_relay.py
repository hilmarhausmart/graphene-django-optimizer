import pytest

import graphene_django_optimizer as gql_optimizer

from .graphql_utils import create_resolve_info
from .models import (
    Item,
)
from .schema import schema
from .test_utils import assert_query_equality
from .test_utils import assert_num_queries


@pytest.mark.django_db
def test_should_return_valid_result_in_a_relay_query():
    Item.objects.create(id=7, name='foo')
    result = schema.execute('''
        query {
            relayItems {
                edges {
                    node {
                        id
                        name
                    }
                }
            }
        }
    ''')
    assert not result.errors
    assert result.data['relayItems']['edges'][0]['node']['id'] == '7'
    assert result.data['relayItems']['edges'][0]['node']['name'] == 'foo'


def test_should_reduce_number_of_queries_in_relay_schema_by_using_select_related():
    info = create_resolve_info(schema, '''
        query {
            relayItems {
                edges {
                    node {
                        id
                        foo
                        parent {
                            id
                        }
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='bar')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.select_related('parent')
    assert_query_equality(items, optimized_items)


def test_should_reduce_number_of_queries_in_relay_schema_by_using_prefetch_related():
    info = create_resolve_info(schema, '''
        query {
            relayItems {
                edges {
                    node {
                        id
                        foo
                        children {
                            id
                            foo
                        }
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.prefetch_related('children')
    assert_query_equality(items, optimized_items)


def test_should_optimize_query_by_only_requesting_id_field():
    try:
        from django.db.models import DEFERRED  # noqa: F401
    except ImportError:
        # Query cannot be optimized if DEFERRED is not present.
        # When the ConnectionField is used, it will throw the following error:
        # Expected value of type "ItemNode" but got: Item_Deferred_item_id_parent_id.
        return
    info = create_resolve_info(schema, '''
        query {
            relayItems {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.only('id')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_should_work_fine_with_page_info_field():
    Item.objects.create(id=7, name='foo')
    Item.objects.create(id=13, name='bar')
    Item.objects.create(id=17, name='foobar')
    result = schema.execute('''
        query {
            relayItems(first: 2) {
                pageInfo {
                    hasNextPage
                }
                edges {
                    node {
                        id
                    }
                }
            }
        }
    ''')
    assert not result.errors
    assert result.data['relayItems']['pageInfo']['hasNextPage'] is True


@pytest.mark.django_db
def test_should_work_fine_with_page_info_field_below_edges_field_when_only_optimization_is_aborted():
    Item.objects.create(id=7, name='foo')
    Item.objects.create(id=13, name='bar')
    Item.objects.create(id=17, name='foobar')
    result = schema.execute('''
        query {
            relayItems(first: 2) {
                edges {
                    node {
                        id
                        foo
                    }
                }
                pageInfo {
                    hasNextPage
                }
            }
        }
    ''')
    assert not result.errors
    assert result.data['relayItems']['pageInfo']['hasNextPage'] is True


@pytest.mark.django_db
def test_should_resolve_nested_variables():
    item_1 = Item.objects.create(id=7, name='foo')
    item_1.children.create(id=8, name='bar')
    variables = {'itemsFirst': 1, 'childrenFirst': 1}
    result = schema.execute('''
        query Query($itemsFirst: Int!, $childrenFirst: Int!) {
            relayItems(first: $itemsFirst) {
                edges {
                    node {
                        relayAllChildren(first: $childrenFirst) {
                            edges {
                                node {
                                    id
                                }
                            }
                        }
                    }
                }
            }
        }
    ''', variables=variables)
    assert not result.errors
    item_edges = result.data['relayItems']['edges']
    assert len(item_edges) == 1
    child_edges = item_edges[0]['node']['relayAllChildren']['edges'][0]
    assert len(child_edges) == 1
    assert child_edges['node']['id'] == '8'


def test_should_optimize_query_when_using_global_id():
    try:
        from django.db.models import DEFERRED  # noqa: F401
    except ImportError:
        # Query cannot be optimized if DEFERRED is not present.
        # When the ConnectionField is used, it will throw the following error:
        # Expected value of type "ItemNode" but got: Item_Deferred_item_id_parent_id.
        return
    info = create_resolve_info(schema, '''
        query {
            relayItemsGlobalId {
                edges {
                    node {
                        id,
                        name
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.query(qs, info)
    optimized_items = qs.only('id', 'name')
    assert_query_equality(items, optimized_items)


def test_should_optimize_query_when_using_global_uuid():
    try:
        from django.db.models import DEFERRED  # noqa: F401
    except ImportError:
        # Query cannot be optimized if DEFERRED is not present.
        # When the ConnectionField is used, it will throw the following error:
        # Expected value of type "ItemNode" but got: Item_Deferred_item_id_parent_id.
        return
    info = create_resolve_info(schema, '''
        query {
            relayItemsGlobalUuid {
                edges {
                    node {
                        id,
                        name
                    }
                }
            }
        }
    ''')
    qs = Item.objects.filter(name='foo')
    items = gql_optimizer.QueryOptimizer(info, id_field='uuid').optimize(qs)
    optimized_items = qs.only('uuid', 'name')
    assert_query_equality(items, optimized_items)


@pytest.mark.django_db
def test_verify_should_return_global_uuid():
    Item.objects.create(id=9, uuid='8ea0da0b-da77-4b11-8fbb-350f59a41854', name='bar')

    with assert_num_queries(2):
        # UUID should be used as a global id.
        result = schema.execute('''
            query {
                relayItemsGlobalUuid {
                    edges {
                        node {
                            id,
                            name
                        }
                    }
                }
            }
        ''')

    # ItemNodeGlobalUUID:8ea0da0b-da77-4b11-8fbb-350f59a41854
    expected_id = 'SXRlbU5vZGVHbG9iYWxVVUlEOjhlYTBkYTBiLWRhNzctNGIxMS04ZmJiLTM1MGY1OWE0MTg1NA=='

    assert not result.errors
    assert result.data['relayItemsGlobalUuid']['edges'][0]['node']['id'] == expected_id
    assert result.data['relayItemsGlobalUuid']['edges'][0]['node']['name'] == 'bar'


@pytest.mark.django_db
def test_prefetch_related_should_include_parent_key_id_in_only():
    item_1 = Item.objects.create(id=10, name='foo')

    item_1.children.create(id=11, name='b')
    item_1.children.create(id=12, name='a')
    item_1.children.create(id=13, name='r')

    # Queries: count, relayItems, children, filteredChildren
    with assert_num_queries(4):
        result = schema.execute('''
            query {
                relayItems {
                    edges {
                        node {
                            id
                            name
                            children {
                                id
                                name
                            },
                            filteredChildren (name: "a") {
                                id
                            }
                        }
                    }
                }
            }
        ''')

    assert not result.errors
    assert result.data['relayItems']['edges'][0]['node']['id'] == '10'
    assert result.data['relayItems']['edges'][0]['node']['name'] == 'foo'

    assert len(result.data['relayItems']['edges'][0]['node']['children']) == 3
    assert result.data['relayItems']['edges'][0]['node']['children'][0]['id'] == '11'
    assert result.data['relayItems']['edges'][0]['node']['children'][0]['name'] == 'b'
    assert result.data['relayItems']['edges'][0]['node']['children'][1]['id'] == '12'
    assert result.data['relayItems']['edges'][0]['node']['children'][1]['name'] == 'a'
    assert result.data['relayItems']['edges'][0]['node']['children'][2]['id'] == '13'
    assert result.data['relayItems']['edges'][0]['node']['children'][2]['name'] == 'r'

    assert len(result.data['relayItems']['edges'][0]['node']['filteredChildren']) == 1
    assert result.data['relayItems']['edges'][0]['node']['filteredChildren'][0]['id'] == '12'
