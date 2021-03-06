from __future__ import unicode_literals

from precisely import assert_that, contains_exactly, equal_to, has_attrs, is_mapping, is_sequence
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import pytest

import graphlayer as g
from graphlayer import schema, sqlalchemy as gsql
import graphlayer.connections
from graphlayer.resolvers import root_object_resolver


class TestExpressionField(object):
    def test_can_get_fields_backed_by_expressions(self):
        Base = sqlalchemy.ext.declarative.declarative_base()

        class BookRow(Base):
            __tablename__ = "book"

            c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
            c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

        engine = sqlalchemy.create_engine("sqlite:///:memory:")

        Base.metadata.create_all(engine)

        session = sqlalchemy.orm.Session(engine)
        session.add(BookRow(c_title="Leave it to Psmith"))
        session.add(BookRow(c_title="Pericles, Prince of Tyre"))
        session.commit()

        Book = g.ObjectType(
            "Book",
            fields=lambda: [
                g.field("title", type=g.String),
            ],
        )

        book_resolver = gsql.sql_table_resolver(
            Book,
            BookRow,
            fields={
                Book.fields.title: gsql.expression(BookRow.c_title),
            },
        )

        resolvers = [book_resolver]

        query = gsql.select(g.ListType(Book)(
            g.key("title", Book.fields.title()),
        ))
        graph_definition = g.define_graph(resolvers)
        graph = graph_definition.create_graph({
            sqlalchemy.orm.Session: session,
        })
        result = graph.resolve(query)

        assert_that(result, contains_exactly(
            has_attrs(
                title="Leave it to Psmith",
            ),
            has_attrs(
                title="Pericles, Prince of Tyre",
            ),
        ))

    def test_can_pass_arguments_to_expression(self):
        Base = sqlalchemy.ext.declarative.declarative_base()

        class BookRow(Base):
            __tablename__ = "book"

            c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
            c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

        engine = sqlalchemy.create_engine("sqlite:///:memory:")

        Base.metadata.create_all(engine)

        session = sqlalchemy.orm.Session(engine)
        session.add(BookRow(c_title="Leave it to Psmith"))
        session.commit()

        Book = g.ObjectType(
            "Book",
            fields=lambda: [
                g.field("title", type=g.String, params=[
                    g.param("truncate", g.Int),
                ]),
            ],
        )

        book_resolver = gsql.sql_table_resolver(
            Book,
            BookRow,
            fields={
                Book.fields.title: lambda graph, field_query: gsql.expression(
                    sqlalchemy.func.substr(BookRow.c_title, 1, field_query.args.truncate),
                ),
            },
        )

        resolvers = [book_resolver]

        query = gsql.select(g.ListType(Book)(
            g.key("title", Book.fields.title(Book.fields.title.params.truncate(8))),
        ))
        graph_definition = g.define_graph(resolvers)
        graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
        result = graph.resolve(query)

        assert_that(result, contains_exactly(
            has_attrs(
                title="Leave it",
            ),
        ))


def test_can_get_constant_fields():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_title="Leave it to Psmith"))
    session.add(BookRow(c_title="Pericles, Prince of Tyre"))
    session.commit()

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("sales", type=g.Int),
            g.field("title", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.sales: gsql.constant(0),
            Book.fields.title: gsql.expression(BookRow.c_title),
        },
    )

    resolvers = [book_resolver]

    query = gsql.select(g.ListType(Book)(
        g.key("sales", Book.fields.sales()),
        g.key("title", Book.fields.title()),
    ))
    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({
        sqlalchemy.orm.Session: session,
    })
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            sales=0,
            title="Leave it to Psmith",
        ),
        has_attrs(
            sales=0,
            title="Pericles, Prince of Tyre",
        ),
    ))


def test_can_fulfil_requests_with_no_expressions():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_title="Leave it to Psmith"))
    session.add(BookRow(c_title="Pericles, Prince of Tyre"))
    session.commit()

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("sales", type=g.Int),
            g.field("title", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.sales: gsql.constant(0),
        },
    )

    resolvers = [book_resolver]

    query = gsql.select(g.ListType(Book)(
        g.key("sales", Book.fields.sales()),
    ))
    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({
        sqlalchemy.orm.Session: session,
    })
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            sales=0,
        ),
        has_attrs(
            sales=0,
        ),
    ))


def test_can_get_field_backed_by_multiple_expressions():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)
        c_year = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_title="Leave it to Psmith", c_year=1923))
    session.add(BookRow(c_title="Pericles, Prince of Tyre", c_year=1607))
    session.commit()

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("description", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.description: gsql.composite(
                (BookRow.c_title, BookRow.c_year),
                lambda title, year: "{} ({})".format(title, year),
            ),
        },
    )

    resolvers = [book_resolver]

    query = gsql.select(g.ListType(Book)(
        g.key("description", Book.fields.description()),
    ))
    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({
        sqlalchemy.orm.Session: session,
    })
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            description="Leave it to Psmith (1923)",
        ),
        has_attrs(
            description="Pericles, Prince of Tyre (1607)",
        ),
    ))


class TestReturnShapeMatchesQueryShape(object):
    @pytest.fixture(autouse=True)
    def setup(self):
        Base = sqlalchemy.ext.declarative.declarative_base()

        class BookRow(Base):
            __tablename__ = "book"

            c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
            c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

        engine = sqlalchemy.create_engine("sqlite:///:memory:")

        Base.metadata.create_all(engine)

        session = sqlalchemy.orm.Session(engine)

        Book = g.ObjectType(
            "Book",
            fields=lambda: [
                g.field("title", type=g.String),
            ],
        )

        book_resolver = gsql.sql_table_resolver(
            Book,
            BookRow,
            fields={
                Book.fields.title: gsql.expression(BookRow.c_title),
            },
        )

        resolvers = [book_resolver]

        graph_definition = g.define_graph(resolvers)
        self.graph = graph_definition.create_graph({
            sqlalchemy.orm.Session: session,
        })
        self.Book = Book
        self.BookRow = BookRow
        self.session = session

    def test_given_there_are_no_rows_then_requesting_list_returns_empty_list(self):
        query = gsql.select(g.ListType(self.Book)(
            g.key("title", self.Book.fields.title()),
        ))
        result = self.resolve(query)

        assert_that(result, contains_exactly())

    def test_given_there_are_rows_then_requesting_list_returns_list(self):
        self.add_books("Leave it to Psmith", "Pericles, Prince of Tyre")

        query = gsql.select(g.ListType(self.Book)(
            g.key("title", self.Book.fields.title()),
        ))
        result = self.resolve(query)

        assert_that(result, contains_exactly(
            has_attrs(
                title="Leave it to Psmith",
            ),
            has_attrs(
                title="Pericles, Prince of Tyre",
            ),
        ))

    def test_given_there_are_no_rows_then_requesting_nullable_returns_null(self):
        query = gsql.select(g.NullableType(self.Book)(
            g.key("title", self.Book.fields.title()),
        ))
        result = self.resolve(query)

        assert_that(result, equal_to(None))

    def test_given_there_is_one_row_then_requesting_nullable_returns_object(self):
        self.add_books("Leave it to Psmith")

        query = gsql.select(g.NullableType(self.Book)(
            g.key("title", self.Book.fields.title()),
        ))
        result = self.resolve(query)

        assert_that(result, has_attrs(title="Leave it to Psmith"))

    def test_given_there_is_more_than_one_row_then_requesting_nullable_raises_error(self):
        self.add_books("Leave it to Psmith", "Pericles, Prince of Tyre")

        query = gsql.select(g.NullableType(self.Book)(
            g.key("title", self.Book.fields.title()),
        ))
        error = pytest.raises(g.GraphError, lambda: self.resolve(query))

        assert_that(str(error.value), equal_to("expected exactly zero or one values but got 2"))

    def test_given_there_are_no_rows_then_requesting_object_raises_error(self):
        query = gsql.select(self.Book(
            g.key("title", self.Book.fields.title()),
        ))
        error = pytest.raises(g.GraphError, lambda: self.resolve(query))

        assert_that(str(error.value), equal_to("expected exactly one value but got 0"))

    def test_given_there_is_one_row_then_requesting_object_returns_object(self):
        self.add_books("Leave it to Psmith")

        query = gsql.select(self.Book(
            g.key("title", self.Book.fields.title()),
        ))
        result = self.resolve(query)

        assert_that(result, has_attrs(title="Leave it to Psmith"))

    def test_given_there_is_more_than_one_row_then_requesting_object_raises_error(self):
        self.add_books("Leave it to Psmith", "Pericles, Prince of Tyre")

        query = gsql.select(self.Book(
            g.key("title", self.Book.fields.title()),
        ))
        error = pytest.raises(g.GraphError, lambda: self.resolve(query))

        assert_that(str(error.value), equal_to("expected exactly one value but got 2"))

    def add_books(self, *titles):
        for title in titles:
            self.session.add(self.BookRow(c_title=title))
        self.session.commit()

    def resolve(self, query):
        return self.graph.resolve(query)


def test_can_filter_results_using_where():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_id=1, c_title="Leave it to Psmith"))
    session.add(BookRow(c_id=2, c_title="Pericles, Prince of Tyre"))

    session.commit()

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: gsql.expression(BookRow.c_title),
        },
    )

    resolvers = (book_resolver, )

    query = gsql.select(g.ListType(Book)(
        g.key("title", Book.fields.title()),
    )).where(BookRow.c_id == 1)

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            title="Leave it to Psmith",
        ),
    ))


def test_can_limit_results_using_limit():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_id=1, c_title="Leave it to Psmith"))
    session.add(BookRow(c_id=2, c_title="Pericles, Prince of Tyre"))
    session.add(BookRow(c_id=3, c_title="Captain Corelli's Mandolin"))

    session.commit()

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: gsql.expression(BookRow.c_title),
        },
    )

    resolvers = (book_resolver, )

    query = gsql.select(g.ListType(Book)(
        g.key("title", Book.fields.title()),
    )).order_by(BookRow.c_title).limit(2)

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, is_sequence(
        has_attrs(title="Captain Corelli's Mandolin"),
        has_attrs(title="Leave it to Psmith"),
    ))


def test_can_order_results_using_order_by():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_id=1, c_title="Leave it to Psmith"))
    session.add(BookRow(c_id=2, c_title="Pericles, Prince of Tyre"))
    session.add(BookRow(c_id=3, c_title="Captain Corelli's Mandolin"))

    session.commit()

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: gsql.expression(BookRow.c_title),
        },
    )

    resolvers = (book_resolver, )

    query = gsql.select(g.ListType(Book)(
        g.key("title", Book.fields.title()),
    )).order_by(BookRow.c_title)

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, is_sequence(
        has_attrs(title="Captain Corelli's Mandolin"),
        has_attrs(title="Leave it to Psmith"),
        has_attrs(title="Pericles, Prince of Tyre"),
    ))


def test_can_group_results_using_group_by():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_author = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_id=1, c_author="PG Wodehouse"))
    session.add(BookRow(c_id=2, c_author="William Shakespeare"))
    session.add(BookRow(c_id=3, c_author="PG Wodehouse"))

    session.commit()

    Author = g.ObjectType(
        "Author",
        fields=lambda: [
            g.field("name", type=g.String),
        ],
    )

    author_resolver = gsql.sql_table_resolver(
        Author,
        BookRow,
        fields={
            Author.fields.name: gsql.expression(BookRow.c_author),
        },
    )

    resolvers = (author_resolver, )

    query = gsql.select(g.ListType(Author)(
        g.key("name", Author.fields.name()),
    )).group_by(BookRow.c_author)

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(name="PG Wodehouse"),
        has_attrs(name="William Shakespeare"),
    ))


class TestSqlQueryBy(object):
    @pytest.fixture(autouse=True)
    def setup(self):
        Base = sqlalchemy.ext.declarative.declarative_base()

        class BookRow(Base):
            __tablename__ = "book"

            c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
            c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

        self.BookRow = BookRow

        engine = sqlalchemy.create_engine("sqlite:///:memory:")

        Base.metadata.create_all(engine)

        session = sqlalchemy.orm.Session(engine)
        session.add(BookRow(c_id=1, c_title="Leave it to Psmith"))
        session.add(BookRow(c_id=2, c_title="Pericles, Prince of Tyre"))
        session.add(BookRow(c_id=3, c_title="Captain Corelli's Mandolin"))

        session.commit()

        self.Book = Book = g.ObjectType(
            "Book",
            fields=lambda: [
                g.field("title", type=g.String),
            ],
        )

        book_resolver = gsql.sql_table_resolver(
            Book,
            BookRow,
            fields={
                Book.fields.title: gsql.expression(BookRow.c_title),
            },
        )

        resolvers = (book_resolver, )

        graph_definition = g.define_graph(resolvers)
        self.graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})

    def test_when_passed_single_expression_then_filters_to_rows_with_that_expression_value_and_indexes_by_that_expression(self):
        query = gsql.select(self.Book(
            g.key("title", self.Book.fields.title()),
        )).by(self.BookRow.c_id, (1, 3))

        result = self.graph.resolve(query)

        assert_that(result, is_mapping({
            1: has_attrs(
                title="Leave it to Psmith",
            ),
            3: has_attrs(
                title="Captain Corelli's Mandolin",
            ),
        }))

    def test_when_passed_singleton_tuple_then_query_by_filters_to_rows_with_that_expression_value_and_indexes_by_that_expression(self):
        query = gsql.select(self.Book(
            g.key("title", self.Book.fields.title()),
        )).by((self.BookRow.c_id, ), ((1, ), (3, )))

        result = self.graph.resolve(query)

        assert_that(result, is_mapping({
            (1, ): has_attrs(
                title="Leave it to Psmith",
            ),
            (3, ): has_attrs(
                title="Captain Corelli's Mandolin",
            ),
        }))

    def test_when_passed_tuple_then_query_by_filters_to_rows_with_that_expression_value_and_indexes_by_that_expression(self):
        key_values = sqlalchemy.union(
            sqlalchemy.orm.Query([sqlalchemy.literal(1), sqlalchemy.literal("Leave it to Psmith")]),
            sqlalchemy.orm.Query([sqlalchemy.literal(3), sqlalchemy.literal("Captain Corelli's Mandolin")]),
        )
        query = gsql.select(self.Book(
            g.key("title", self.Book.fields.title()),
        )).by((self.BookRow.c_id, self.BookRow.c_title), key_values)

        result = self.graph.resolve(query)

        assert_that(result, is_mapping({
            (1, "Leave it to Psmith"): has_attrs(
                title="Leave it to Psmith",
            ),
            (3, "Captain Corelli's Mandolin"): has_attrs(
                title="Captain Corelli's Mandolin",
            ),
        }))


def test_can_recursively_resolve_selected_fields():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class AuthorRow(Base):
        __tablename__ = "author"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_name = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)
        c_author_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(AuthorRow.c_id))

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(AuthorRow(c_id=1, c_name="PG Wodehouse"))
    session.add(AuthorRow(c_id=2, c_name="William Shakespeare"))
    session.add(BookRow(c_title="Leave it to Psmith", c_author_id=1))
    session.add(BookRow(c_title="Pericles, Prince of Tyre", c_author_id=2))

    session.commit()

    Root = g.ObjectType(
        "Root",
        fields=lambda: [
            g.field("books", type=g.ListType(Book)),
        ],
    )

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("author", type=Author),
            g.field("title", type=g.String),
        ],
    )

    Author = g.ObjectType(
        "Author",
        fields=lambda: [
            g.field("name", type=g.String),
        ],
    )

    resolve_root = root_object_resolver(Root)

    @resolve_root.field(Root.fields.books)
    def resolve_root_field_books(graph, query, args):
        return graph.resolve(gsql.select(query))

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: gsql.expression(BookRow.c_title),
            Book.fields.author: lambda graph, field_query: gsql.join(
                key=BookRow.c_author_id,
                resolve=lambda author_ids: graph.resolve(
                    gsql.select(field_query.type_query).by(AuthorRow.c_id, author_ids),
                ),
            ),
        },
    )

    author_resolver = gsql.sql_table_resolver(
        Author,
        AuthorRow,
        fields={
            Author.fields.name: gsql.expression(AuthorRow.c_name),
        },
    )
    resolvers = [resolve_root, book_resolver, author_resolver]

    query = Root(
        g.key("books", Root.fields.books(
            g.key("author", Book.fields.author(
                g.key("name", Author.fields.name()),
            )),
            g.key("title", Book.fields.title()),
        )),
    )

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, has_attrs(
        books=contains_exactly(
            has_attrs(
                author=has_attrs(name="PG Wodehouse"),
                title="Leave it to Psmith",
            ),
            has_attrs(
                author=has_attrs(name="William Shakespeare"),
                title="Pericles, Prince of Tyre",
            ),
        ),
    ))


def test_can_resolve_many_to_one_field():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(LeftRow(c_id=1, c_value="one"))
    session.add(RightRow(c_id=1, c_value="two"))
    session.add(LeftRow(c_id=2, c_value="three"))
    session.add(RightRow(c_id=2, c_value="four"))
    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("right", type=Right),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.right: lambda graph, field_query: gsql.join(
                key=LeftRow.c_id,
                resolve=lambda ids: graph.resolve(
                    gsql.select(field_query.type_query).by(RightRow.c_id, ids),
                ),
            ),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("right", Left.fields.right(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            value="one",
            right=has_attrs(
                value="two",
            ),
        ),
        has_attrs(
            value="three",
            right=has_attrs(
                value="four",
            ),
        ),
    ))


def test_can_resolve_many_to_one_or_zero_field():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(LeftRow(c_id=1, c_value="one"))
    session.add(RightRow(c_id=1, c_value="two"))
    session.add(LeftRow(c_id=2, c_value="three"))
    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("right", type=g.NullableType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.right: lambda graph, field_query: gsql.join(
                key=LeftRow.c_id,
                resolve=lambda ids: graph.resolve(
                    gsql.select(field_query.type_query).by(RightRow.c_id, ids),
                ),
            ),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("right", Left.fields.right(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            value="one",
            right=has_attrs(
                value="two",
            ),
        ),
        has_attrs(
            value="three",
            right=None,
        ),
    ))


def test_can_resolve_one_to_many_field():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_left_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(LeftRow.c_id))
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)

    session.add(LeftRow(c_id=1, c_value="left 1"))
    session.add(RightRow(c_left_id=1, c_value="right 1a"))
    session.add(RightRow(c_left_id=1, c_value="right 1b"))

    session.add(LeftRow(c_id=2, c_value="left 2"))

    session.add(LeftRow(c_id=3, c_value="left 3"))
    session.add(RightRow(c_left_id=3, c_value="right 3"))
    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("rights", type=g.ListType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.rights: lambda graph, field_query: gsql.join(
                key=LeftRow.c_id,
                resolve=lambda ids: graph.resolve(
                    gsql.select(field_query.type_query).by(RightRow.c_left_id, ids),
                ),
            ),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("rights", Left.fields.rights(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            value="left 1",
            rights=contains_exactly(
                has_attrs(value="right 1a"),
                has_attrs(value="right 1b"),
            ),
        ),
        has_attrs(
            value="left 2",
            rights=contains_exactly(),
        ),
        has_attrs(
            value="left 3",
            rights=contains_exactly(
                has_attrs(value="right 3"),
            ),
        ),
    ))


def test_can_resolve_many_to_many_join_through_association_table():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class AssociationRow(Base):
        __tablename__ = "association"

        c_left_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_right_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)

    session.add(LeftRow(c_id=1, c_value="left 1"))
    session.add(RightRow(c_id=101, c_value="right 1a"))
    session.add(RightRow(c_id=102, c_value="right 1b"))
    session.add(AssociationRow(c_left_id=1, c_right_id=101))
    session.add(AssociationRow(c_left_id=1, c_right_id=102))

    session.add(LeftRow(c_id=2, c_value="left 2"))

    session.add(LeftRow(c_id=3, c_value="left 3"))
    session.add(RightRow(c_id=103, c_value="right 3"))
    session.add(AssociationRow(c_left_id=3, c_right_id=103))

    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("rights", type=g.ListType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.rights: lambda graph, field_query: gsql.join(
                key=LeftRow.c_id,
                association=gsql.association(
                    AssociationRow,
                    left_key=AssociationRow.c_left_id,
                    right_key=AssociationRow.c_right_id,
                ),
                resolve=lambda right_ids: graph.resolve(
                    gsql.select(field_query.type_query).by(RightRow.c_id, right_ids),
                ),
            ),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("rights", Left.fields.rights(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            value="left 1",
            rights=contains_exactly(
                has_attrs(value="right 1a"),
                has_attrs(value="right 1b"),
            ),
        ),
        has_attrs(
            value="left 2",
            rights=contains_exactly(),
        ),
        has_attrs(
            value="left 3",
            rights=contains_exactly(
                has_attrs(value="right 3"),
            ),
        ),
    ))


def test_can_resolve_many_to_one_join_through_association_table():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class AssociationRow(Base):
        __tablename__ = "association"

        c_left_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_right_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)

    session.add(LeftRow(c_id=1, c_value="left 1"))
    session.add(RightRow(c_id=101, c_value="right 1"))
    session.add(AssociationRow(c_left_id=1, c_right_id=101))

    session.add(LeftRow(c_id=2, c_value="left 2"))
    session.add(RightRow(c_id=102, c_value="right 2"))
    session.add(AssociationRow(c_left_id=2, c_right_id=102))

    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("right", type=Right),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.right: lambda graph, field_query: gsql.join(
                key=LeftRow.c_id,
                association=gsql.association(
                    AssociationRow,
                    left_key=AssociationRow.c_left_id,
                    right_key=AssociationRow.c_right_id,
                ),
                resolve=lambda right_ids: graph.resolve(
                    gsql.select(field_query.type_query).by(RightRow.c_id, right_ids),
                ),
            ),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("right", Left.fields.right(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            value="left 1",
            right=has_attrs(value="right 1"),
        ),
        has_attrs(
            value="left 2",
            right=has_attrs(value="right 2"),
        ),
    ))


def test_can_resolve_many_to_one_or_zero_join_through_association_table():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class AssociationRow(Base):
        __tablename__ = "association"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_left_id = sqlalchemy.Column(sqlalchemy.Integer)
        c_right_id = sqlalchemy.Column(sqlalchemy.Integer)

    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)

    session.add(LeftRow(c_id=1, c_value="left 1"))
    session.add(RightRow(c_id=101, c_value="right 1"))
    session.add(AssociationRow(c_left_id=1, c_right_id=101))

    session.add(LeftRow(c_id=2, c_value="left 2"))

    session.add(LeftRow(c_id=3, c_value="left 3"))
    session.add(RightRow(c_id=103, c_value="right 3"))
    session.add(AssociationRow(c_left_id=3, c_right_id=103))

    session.add(LeftRow(c_id=4, c_value="left 4"))
    session.add(AssociationRow(c_left_id=4, c_right_id=104))

    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("right", type=g.NullableType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.right: lambda graph, field_query: gsql.join(
                key=LeftRow.c_id,
                association=gsql.association(
                    AssociationRow,
                    left_key=AssociationRow.c_left_id,
                    right_key=AssociationRow.c_right_id,
                ),
                resolve=lambda right_ids: graph.resolve(
                    gsql.select(field_query.type_query).by(RightRow.c_id, right_ids),
                ),
            ),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("right", Left.fields.right(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            value="left 1",
            right=has_attrs(value="right 1"),
        ),
        has_attrs(
            value="left 2",
            right=None,
        ),
        has_attrs(
            value="left 3",
            right=has_attrs(value="right 3"),
        ),
        has_attrs(
            value="left 4",
            right=None,
        ),
    ))


def test_can_resolve_join_through_association_query():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class AssociationRow(Base):
        __tablename__ = "association"

        c_left_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_right_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)

    session.add(LeftRow(c_id=1, c_value="left 1"))
    session.add(RightRow(c_id=101, c_value="right 1a"))
    session.add(RightRow(c_id=102, c_value="right 1b"))
    session.add(AssociationRow(c_left_id=1, c_right_id=101))
    session.add(AssociationRow(c_left_id=1, c_right_id=102))

    session.add(LeftRow(c_id=2, c_value="left 2"))

    session.add(LeftRow(c_id=3, c_value="left 3"))
    session.add(RightRow(c_id=103, c_value="right 3"))
    session.add(AssociationRow(c_left_id=3, c_right_id=103))

    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("rights", type=g.ListType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.rights: lambda graph, field_query: gsql.join(
                key=LeftRow.c_id,
                association=gsql.association(
                    sqlalchemy.orm.Query([]).select_from(AssociationRow),
                    left_key=AssociationRow.c_left_id,
                    right_key=AssociationRow.c_right_id,
                ),
                resolve=lambda right_ids: graph.resolve(
                    gsql.select(field_query.type_query).by(RightRow.c_id, right_ids),
                ),
            ),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("rights", Left.fields.rights(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            value="left 1",
            rights=contains_exactly(
                has_attrs(value="right 1a"),
                has_attrs(value="right 1b"),
            ),
        ),
        has_attrs(
            value="left 2",
            rights=contains_exactly(),
        ),
        has_attrs(
            value="left 3",
            rights=contains_exactly(
                has_attrs(value="right 3"),
            ),
        ),
    ))


def test_when_distinct_is_true_then_only_unique_associations_are_selected():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class AssociationRow(Base):
        __tablename__ = "association"

        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_left_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
        c_right_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)

    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)

    session.add(LeftRow(c_id=1, c_value="left 1"))
    session.add(RightRow(c_id=101, c_value="right 1"))
    session.add(AssociationRow(c_left_id=1, c_right_id=101))
    session.add(AssociationRow(c_left_id=1, c_right_id=101))

    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("rights", type=g.ListType(Right)),
            g.field("distinct_rights", type=g.ListType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields=lambda: {
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.rights: field_rights(distinct=False),
            Left.fields.distinct_rights: field_rights(distinct=True),
        },
    )

    def field_rights(*, distinct):
        return lambda graph, field_query: gsql.join(
            key=LeftRow.c_id,
            association=gsql.association(
                AssociationRow,
                left_key=AssociationRow.c_left_id,
                right_key=AssociationRow.c_right_id,
                distinct=distinct,
            ),
            resolve=lambda right_ids: graph.resolve(
                gsql.select(field_query.type_query).by(RightRow.c_id, right_ids),
            ),
        )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("rights", Left.fields.rights(
            g.key("value", Right.fields.value()),
        )),
        g.key("distinct_rights", Left.fields.distinct_rights(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            rights=contains_exactly(
                has_attrs(value="right 1"),
                has_attrs(value="right 1"),
            ),
            distinct_rights=contains_exactly(
                has_attrs(value="right 1"),
            ),
        ),
    ))


def test_association_table_can_be_filtered_explicitly():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class AssociationRow(Base):
        __tablename__ = "association"

        c_left_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_right_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)

    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)

    session.add(LeftRow(c_id=1, c_value="left 1"))
    session.add(RightRow(c_id=101, c_value="right 1a"))
    session.add(RightRow(c_id=102, c_value="right 1b"))
    session.add(AssociationRow(c_left_id=1, c_right_id=101))
    session.add(AssociationRow(c_left_id=1, c_right_id=102))

    session.add(LeftRow(c_id=2, c_value="left 2"))

    session.add(LeftRow(c_id=3, c_value="left 3"))
    session.add(RightRow(c_id=103, c_value="right 3"))
    session.add(AssociationRow(c_left_id=3, c_right_id=103))

    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("rights", type=g.ListType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields=lambda: {
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.rights: left_field_rights,
        },
    )

    def left_field_rights(graph, field_query):
        def association(left_ids):
            associations_table = sqlalchemy.orm.Query([
                AssociationRow.c_left_id,
                AssociationRow.c_right_id,
            ]) \
                .select_from(AssociationRow) \
                .filter(AssociationRow.c_left_id.in_(left_ids)) \
                .subquery()

            return gsql.association(
                associations_table,
                left_key=associations_table.c.c_left_id,
                right_key=associations_table.c.c_right_id,
                filtered_by_left_key=True,
            )

        return gsql.join(
            key=LeftRow.c_id,
            association=association,
            resolve=lambda right_ids: graph.resolve(
                gsql.select(field_query.type_query).by(RightRow.c_id, right_ids),
            ),
        )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("rights", Left.fields.rights(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            value="left 1",
            rights=contains_exactly(
                has_attrs(value="right 1a"),
                has_attrs(value="right 1b"),
            ),
        ),
        has_attrs(
            value="left 2",
            rights=contains_exactly(),
        ),
        has_attrs(
            value="left 3",
            rights=contains_exactly(
                has_attrs(value="right 3"),
            ),
        ),
    ))





def test_association_can_have_explicit_order():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class AssociationRow(Base):
        __tablename__ = "association"

        c_left_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_right_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        index = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)

    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)

    session.add(LeftRow(c_id=1, c_value="left 1"))
    session.add(RightRow(c_id=101, c_value="right 1a"))
    session.add(RightRow(c_id=102, c_value="right 1c"))
    session.add(RightRow(c_id=103, c_value="right 1b"))
    session.add(AssociationRow(c_left_id=1, c_right_id=101, index=1))
    session.add(AssociationRow(c_left_id=1, c_right_id=102, index=3))
    session.add(AssociationRow(c_left_id=1, c_right_id=103, index=2))

    session.add(LeftRow(c_id=2, c_value="left 2"))
    session.add(RightRow(c_id=104, c_value="right 2c"))
    session.add(RightRow(c_id=105, c_value="right 2a"))
    session.add(RightRow(c_id=106, c_value="right 2b"))
    session.add(AssociationRow(c_left_id=2, c_right_id=104, index=3))
    session.add(AssociationRow(c_left_id=2, c_right_id=105, index=1))
    session.add(AssociationRow(c_left_id=2, c_right_id=106, index=2))

    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("rights", type=g.ListType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.rights: lambda graph, field_query: gsql.join(
                key=LeftRow.c_id,
                association=gsql.association(
                    AssociationRow,
                    left_key=AssociationRow.c_left_id,
                    right_key=AssociationRow.c_right_id,
                    order_by=AssociationRow.index,
                ),
                resolve=lambda right_ids: graph.resolve(
                    gsql.select(field_query.type_query).by(RightRow.c_id, right_ids),
                ),
            ),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("rights", Left.fields.rights(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            value="left 1",
            rights=is_sequence(
                has_attrs(value="right 1a"),
                has_attrs(value="right 1b"),
                has_attrs(value="right 1c"),
            ),
        ),
        has_attrs(
            value="left 2",
            rights=is_sequence(
                has_attrs(value="right 2a"),
                has_attrs(value="right 2b"),
                has_attrs(value="right 2c"),
            ),
        ),
    ))


def test_can_join_tables_using_multi_column_key():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class LeftRow(Base):
        __tablename__ = "left"

        c_id_1 = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_id_2 = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    class RightRow(Base):
        __tablename__ = "right"

        c_id_1 = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_id_2 = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(LeftRow(c_id_1=1, c_id_2=2, c_value="one"))
    session.add(RightRow(c_id_1=1, c_id_2=2, c_value="two"))
    session.add(LeftRow(c_id_1=1, c_id_2=3, c_value="three"))
    session.add(RightRow(c_id_1=1, c_id_2=3, c_value="four"))
    session.commit()

    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.String),
            g.field("right", type=Right),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.right: lambda graph, field_query: gsql.join(
                key=(LeftRow.c_id_1, LeftRow.c_id_2),
                resolve=lambda left_ids: graph.resolve(
                    gsql.select(field_query.type_query).by((RightRow.c_id_1, RightRow.c_id_2), left_ids),
                ),
            ),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("right", Left.fields.right(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            value="one",
            right=has_attrs(
                value="two",
            ),
        ),
        has_attrs(
            value="three",
            right=has_attrs(
                value="four",
            ),
        ),
    ))


def test_can_map_values_from_sql_expression():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_title="Leave it to Psmith"))
    session.add(BookRow(c_title="Pericles, Prince of Tyre"))
    session.commit()

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("initial", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.initial: gsql.expression(BookRow.c_title).map_value(lambda title: title[0]),
        },
    )

    resolvers = [book_resolver]

    query = gsql.select(g.ListType(Book)(
        g.key("initial", Book.fields.initial()),
    ))
    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({
        sqlalchemy.orm.Session: session,
    })
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(initial="L"),
        has_attrs(initial="P"),
    ))


class TestTags(object):
    def test_tag_can_be_used_to_distinguish_queries_on_same_graph_type(self):
        Base = sqlalchemy.ext.declarative.declarative_base()

        class AuthorRow(Base):
            __tablename__ = "author"

            c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
            c_name = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

        class ReaderRow(Base):
            __tablename__ = "reader"

            c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
            c_name = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

        engine = sqlalchemy.create_engine("sqlite:///:memory:")

        Base.metadata.create_all(engine)

        session = sqlalchemy.orm.Session(engine)
        session.add(AuthorRow(c_name="PG Wodehouse"))
        session.add(ReaderRow(c_name="Matilda"))
        session.commit()

        Person = g.ObjectType(
            "Person",
            fields=lambda: [
                g.field("name", type=g.String),
            ],
        )

        author_resolver = gsql.sql_table_resolver(
            (Person, "author"),
            AuthorRow,
            fields={
                Person.fields.name: gsql.expression(AuthorRow.c_name),
            },
        )

        reader_resolver = gsql.sql_table_resolver(
            (Person, "reader"),
            ReaderRow,
            fields={
                Person.fields.name: gsql.expression(ReaderRow.c_name),
            },
        )

        resolvers = [author_resolver, reader_resolver]

        graph_definition = g.define_graph(resolvers)
        graph = graph_definition.create_graph({
            sqlalchemy.orm.Session: session,
        })

        authors = graph.resolve(
            gsql.select(
                g.ListType(Person)(
                    g.key("name", Person.fields.name()),
                ),
                tag=(Person, "author"),
            ),
        )

        assert_that(authors, contains_exactly(
            has_attrs(name="PG Wodehouse"),
        ))

        readers = graph.resolve(
            gsql.select(
                g.ListType(Person)(
                    g.key("name", Person.fields.name()),
                ),
                tag=(Person, "reader"),
            ),
        )

        assert_that(readers, contains_exactly(
            has_attrs(name="Matilda"),
        ))


def test_when_type_is_object_then_typename_field_is_resolved():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_title="Leave it to Psmith"))
    session.commit()

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: gsql.expression(BookRow.c_title),
        },
    )

    resolvers = [book_resolver]

    query = gsql.select(g.ListType(Book)(
        g.key("title", Book.fields.title()),
        g.key("type", schema.typename_field()),
    ))
    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({
        sqlalchemy.orm.Session: session,
    })
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            title="Leave it to Psmith",
            type="Book",
        ),
    ))


def test_when_type_is_interface_then_typename_field_is_unresolved():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_title="Leave it to Psmith"))
    session.commit()

    Book = g.InterfaceType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: gsql.expression(BookRow.c_title),
        },
    )

    resolvers = [book_resolver]

    query = gsql.select(g.ListType(Book)(
        g.key("title", Book.fields.title()),
        g.key("type", schema.typename_field()),
    ))
    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({
        sqlalchemy.orm.Session: session,
    })

    error = pytest.raises(g.GraphError, lambda: graph.resolve(query))
    assert_that(str(error.value), equal_to("Resolver missing for field type_name"))


def test_connection_uses_primary_key_to_order_objects():
    Base = sqlalchemy.ext.declarative.declarative_base()

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_title="Leave it to Psmith"))
    session.add(BookRow(c_title="The Gentleman's Guide to Vice and Virtue"))
    session.add(BookRow(c_title="Catch-22"))
    session.commit()

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: gsql.expression(BookRow.c_title),
        },
    )

    books_connection = gsql.forward_connection(
        connection_type_name="BooksConnection",
        node_type=Book,
        key=BookRow.c_id,
        select_by_key=lambda query, keys: gsql.select(query).by(BookRow.c_id, keys),
    )
    BooksConnection = books_connection.Connection
    PageInfo = graphlayer.connections.PageInfo

    Query = g.ObjectType(
        "Query",
        fields=lambda: (
            books_connection.field("books_connection"),
        ),
    )

    resolve_query = g.root_object_resolver(Query)

    @resolve_query.field(Query.fields.books_connection)
    def resolve_query_field_books_connection(graph, query, args):
        return graph.resolve(books_connection.select_field(query, args=args))

    resolvers = (book_resolver, books_connection.resolvers, resolve_query)
    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({
        sqlalchemy.orm.Session: session,
    })

    result = graph.resolve(
        Query(
            g.key("books", Query.fields.books_connection(
                Query.fields.books_connection.params.first(2),

                g.key("nodes", BooksConnection.fields.nodes(
                    g.key("title", Book.fields.title()),
                )),
                g.key("page_info", BooksConnection.fields.page_info(
                    g.key("has_next_page", PageInfo.fields.has_next_page()),
                )),
            )),
        )
    )

    assert_that(result, has_attrs(
        books=has_attrs(
            nodes=contains_exactly(
                has_attrs(title="Leave it to Psmith"),
                has_attrs(title="The Gentleman's Guide to Vice and Virtue"),
            ),
            page_info=has_attrs(has_next_page=True),
        ),
    ))


def test_sql_query_type_str():
    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.String),
        ],
    )
    query = gsql.select(Book(
        g.key("title", Book.fields.title()),
    ))

    assert_that(str(query.type), equal_to("(graphlayer.sqlalchemy.select, ObjectType(name='Book'))"))
