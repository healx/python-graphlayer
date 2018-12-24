import enum

from precisely import assert_that, equal_to, has_attrs
import pytest

from graphlayer import schema
from graphlayer.representations import Object


def test_when_param_does_not_exist_on_params_then_error_is_raised():
    params = schema.Params("book", {})
    
    error = pytest.raises(ValueError, lambda: params.author)
    
    assert_that(str(error.value), equal_to("book has no param author"))


def test_when_field_does_not_exist_on_object_type_then_error_is_raised():
    book = schema.ObjectType("Book", fields=(
        schema.field("title", schema.String),
    ))
    
    error = pytest.raises(ValueError, lambda: book.fields.author)
    
    assert_that(str(error.value), equal_to("Book has no field author"))


def test_given_input_field_has_default_when_input_field_is_not_set_then_default_is_used():
    Input = schema.InputObjectType(
        "Input",
        fields=(
            schema.input_field("field0", type=schema.Int, default=None),
            schema.input_field("field1", type=schema.Int, default=42),
        ),
    )
    
    input_value = Input()
    assert_that(input_value, has_attrs(
        field0=None,
        field1=42,
    ))


def test_given_input_field_has_no_default_when_input_field_is_not_set_then_error_is_raised():
    Input = schema.InputObjectType(
        "Input",
        fields=(
            schema.input_field("field0", type=schema.Int),
        ),
    )
    
    error = pytest.raises(ValueError, lambda: Input())
    assert_that(str(error.value), equal_to("missing value for field0"))


def test_given_field_arg_has_default_when_field_arg_is_not_set_then_default_is_used():
    Root = schema.ObjectType(
        "Root",
        fields=(
            schema.field("one", type=schema.Int, params=[
                schema.param("arg0", type=schema.Int, default=None),
                schema.param("arg1", type=schema.Int, default=42),
            ]),
        ),
    )
    
    field_query = Root.fields.one()
    assert_that(field_query.args, has_attrs(
        arg0=None,
        arg1=42,
    ))


def test_given_field_arg_has_no_default_when_field_arg_is_not_set_then_error_is_raised():
    Root = schema.ObjectType(
        "Root",
        fields=(
            schema.field("one", type=schema.Int, params=[
                schema.param("arg0", type=schema.Int),
            ]),
        ),
    )
    
    error = pytest.raises(ValueError, lambda: Root.fields.one())
    assert_that(str(error.value), equal_to("missing value for arg0"))


class TestToJsonValue(object):
    def test_bool_is_unchanged(self):
        query = schema.Boolean()
        assert_that(query.to_json_value(True), equal_to(True))

    def test_float_is_unchanged(self):
        query = schema.Float()
        assert_that(query.to_json_value(4.2), equal_to(4.2))

    def test_int_is_unchanged(self):
        query = schema.Int()
        assert_that(query.to_json_value(42), equal_to(42))

    def test_string_is_unchanged(self):
        query = schema.String()
        assert_that(query.to_json_value("42"), equal_to("42"))

    def test_enums_are_converted_to_graphql_enums(self):
        class Season(enum.Enum):
            winter = "WINTER"
            spring = "SPRING"
            summer = "SUMMER"
            autumn = "AUTUMN"

        SeasonGraphType = schema.EnumType(Season)
        query = SeasonGraphType()
        assert_that(query.to_json_value(Season.winter), equal_to("WINTER"))

    def test_objects_are_converted_to_dicts(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        query = Book(book_title=Book.fields.title())
        value = Object(dict(book_title="Orbiting the Giant Hairball"))
        assert_that(query.to_json_value(value), equal_to({
            "book_title": "Orbiting the Giant Hairball",
        }))

    def test_objects_convert_fields_to_json_values(self):
        Author = schema.ObjectType("Author", fields=(
            schema.field("name", schema.String),
        ))
        Book = schema.ObjectType("Book", fields=(
            schema.field("author", Author),
        ))
        query = Book(author=Book.fields.author(name=Author.fields.name()))
        value = Object(dict(
            author=Object(dict(
                name="Gordon A. Mackenzie",
            )),
        ))
        assert_that(query.to_json_value(value), equal_to({
            "author": {
                "name": "Gordon A. Mackenzie",
            },
        }))

    def test_when_value_is_none_then_nullable_value_is_converted_to_none(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        NullableBook = schema.NullableType(Book)
        query = NullableBook(book_title=Book.fields.title())
        assert_that(query.to_json_value(None), equal_to(None))

    def test_when_value_is_not_none_then_nullable_value_is_converted_using_element_query(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        NullableBook = schema.NullableType(Book)
        query = NullableBook(book_title=Book.fields.title())
        value = Object(dict(book_title="Orbiting the Giant Hairball"))
        assert_that(query.to_json_value(value), equal_to({
            "book_title": "Orbiting the Giant Hairball",
        }))

    def test_lists_convert_elements_to_json_values(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        BookList = schema.ListType(Book)
        query = BookList(book_title=Book.fields.title())
        value = Object(dict(book_title="Orbiting the Giant Hairball"))
        assert_that(query.to_json_value([value]), equal_to([
            {
                "book_title": "Orbiting the Giant Hairball",
            },
        ]))
