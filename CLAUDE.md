# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Setup virtual environment and install dependencies
make bootstrap

# Run all tests (pyflakes linting + pytest)
make test

# Run only pytest tests
make test-pytest

# Run only pyflakes linting
make test-pyflakes

# Run a single test file
pytest tests/test_core.py

# Run a specific test
pytest tests/test_core.py::test_resolver_is_dispatched_using_type_of_query

# Run tests across all Python versions with tox
make test-all
```

## Architecture Overview

GraphLayer is a high-performance GraphQL library that resolves queries per request shape rather than per response node. This avoids the N+1 problem without DataLoader-style batching.

### Core Concepts

**Graph and Resolvers** (`graphlayer/core.py`): The `Graph` dispatches queries to resolvers based on `query.type`. Resolvers are registered with `@g.resolver(type)` and receive `(graph, query)`. Use `graph.resolve(query)` to delegate to other resolvers.

**Schema Types** (`graphlayer/schema.py`): Defines GraphQL types - `ObjectType`, `InterfaceType`, `ListType`, `NullableType`, `EnumType`, `InputObjectType`, and scalars (`Int`, `String`, `Boolean`, `Float`). Object types have `fields` defined via `g.field(name, type, params)`.

**Queries**: Each type has a corresponding query class (`ObjectQuery`, `ListQuery`, `ScalarQuery`, etc.). Resolvers receive queries that describe what fields/data are requested, enabling optimized data fetching.

**Dependency Injection**: Use `@g.dependencies(name=Key)` to inject dependencies into resolvers. Dependencies are provided when creating the graph via `graph_definition.create_graph({Key: value})`.

### Module Structure

- `graphlayer/` - Core library
  - `core.py` - Graph, resolvers, dependency injection
  - `schema.py` - Type system and query classes
  - `resolvers.py` - Helper functions (`root_object_resolver`, `create_object_builder`)
  - `sqlalchemy.py` - SQLAlchemy integration (`sql_table_resolver`, `select`, `join`, `expression`)
  - `connections.py` - Relay-style pagination
  - `unions.py` - Union type resolution
  - `graphql/` - GraphQL parsing and schema generation
- `tests/` - Test suite using pytest and precisely matchers
- `examples/` - Example applications including SQLAlchemy integration

### Key Patterns

**Root Resolver Pattern**:
```python
resolve_root = g.root_object_resolver(Root)

@resolve_root.field(Root.fields.books)
def resolve_books(graph, query, args):
    return graph.resolve(gsql.select(query).where(...))
```

**SQLAlchemy Table Resolver**:
```python
resolve_books = gsql.sql_table_resolver(
    Book, BookRecord,
    fields={
        Book.fields.title: gsql.expression(BookRecord.title),
        Book.fields.author: lambda graph, field_query: gsql.join(
            key=BookRecord.author_id,
            resolve=lambda ids: graph.resolve(gsql.select(field_query.type_query).by(AuthorRecord.id, ids)),
        ),
    },
)
```

**Custom Query Types**: Create custom query classes with a `type` attribute to enable filtering/keying:
```python
class BookQuery:
    def __init__(self, object_query, genre=None):
        self.type = BookQuery
        self.object_query = object_query
        self.genre = genre
```