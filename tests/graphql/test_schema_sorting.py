"""Tests for schema sorting functionality."""
import enum

from precisely import assert_that, contains_exactly, equal_to

import graphlayer as g
from graphlayer.graphql.schema import create_graphql_schema


def test_fields_are_sorted_alphabetically_when_sort_schema_is_true():
    """Test that object type fields are sorted alphabetically."""
    Root = g.ObjectType("Root", fields=(
        g.field("zebra", g.String),
        g.field("apple", g.String),
        g.field("mango", g.String),
        g.field("banana", g.String),
    ))

    schema = create_graphql_schema(query_type=Root, sort_schema=True)
    field_names = list(schema.graphql_schema.query_type.fields.keys())

    assert_that(field_names, equal_to(["apple", "banana", "mango", "zebra"]))


def test_fields_preserve_definition_order_when_sort_schema_is_false():
    """Test that object type fields preserve definition order when not sorted."""
    Root = g.ObjectType("Root", fields=(
        g.field("zebra", g.String),
        g.field("apple", g.String),
        g.field("mango", g.String),
        g.field("banana", g.String),
    ))

    schema = create_graphql_schema(query_type=Root, sort_schema=False)
    field_names = list(schema.graphql_schema.query_type.fields.keys())

    assert_that(field_names, equal_to(["zebra", "apple", "mango", "banana"]))


def test_field_arguments_are_sorted_alphabetically_when_sort_schema_is_true():
    """Test that field arguments are sorted alphabetically."""
    Root = g.ObjectType("Root", fields=(
        g.field("value", g.String, params=(
            g.param("zebra", g.Int),
            g.param("apple", g.Int),
            g.param("mango", g.Int),
            g.param("banana", g.Int),
        )),
    ))

    schema = create_graphql_schema(query_type=Root, sort_schema=True)
    arg_names = list(schema.graphql_schema.query_type.fields["value"].args.keys())

    assert_that(arg_names, equal_to(["apple", "banana", "mango", "zebra"]))


def test_enum_values_are_sorted_alphabetically_when_sort_schema_is_true():
    """Test that enum values are sorted alphabetically."""
    class Color(enum.Enum):
        red = "RED"
        green = "GREEN"
        blue = "BLUE"
        yellow = "YELLOW"

    ColorType = g.EnumType(Color)

    Root = g.ObjectType("Root", fields=(
        g.field("color", ColorType),
    ))

    schema = create_graphql_schema(query_type=Root, sort_schema=True)

    # Find the Color enum type in the schema
    color_enum_type = None
    for type_obj in schema.graphql_schema.type_map.values():
        if hasattr(type_obj, 'name') and type_obj.name == "Color":
            color_enum_type = type_obj
            break

    assert color_enum_type is not None, "Color enum type not found in schema"

    enum_value_names = list(color_enum_type.values.keys())
    assert_that(enum_value_names, equal_to(["BLUE", "GREEN", "RED", "YELLOW"]))


def test_nested_type_fields_are_sorted_when_sort_schema_is_true():
    """Test that nested object type fields are also sorted."""
    NestedType = g.ObjectType("Nested", fields=(
        g.field("zebra", g.String),
        g.field("apple", g.String),
    ))

    Root = g.ObjectType("Root", fields=(
        g.field("nested", NestedType),
    ))

    schema = create_graphql_schema(query_type=Root, sort_schema=True)

    # Get the Nested type from the schema
    nested_type = schema.graphql_schema.type_map["Nested"]
    field_names = list(nested_type.fields.keys())

    assert_that(field_names, equal_to(["apple", "zebra"]))


def test_mutation_fields_are_sorted_when_sort_schema_is_true():
    """Test that mutation type fields are sorted alphabetically."""
    Root = g.ObjectType("Root", fields=(
        g.field("value", g.String),
    ))

    Mutation = g.ObjectType("Mutation", fields=(
        g.field("updateZebra", g.String),
        g.field("createApple", g.String),
        g.field("deleteMango", g.String),
    ))

    schema = create_graphql_schema(
        query_type=Root,
        mutation_type=Mutation,
        sort_schema=True,
    )

    mutation_field_names = list(schema.graphql_schema.mutation_type.fields.keys())
    assert_that(mutation_field_names, equal_to(["createApple", "deleteMango", "updateZebra"]))


def test_input_object_fields_are_sorted_when_sort_schema_is_true():
    """Test that input object type fields are sorted alphabetically."""
    InputType = g.InputObjectType("Input", fields=(
        g.input_field("zebra", g.String),
        g.input_field("apple", g.String),
        g.input_field("mango", g.String),
    ))

    Root = g.ObjectType("Root", fields=(
        g.field("process", g.String, params=(
            g.param("input", InputType),
        )),
    ))

    schema = create_graphql_schema(query_type=Root, sort_schema=True)

    input_type = schema.graphql_schema.type_map["Input"]
    field_names = list(input_type.fields.keys())

    assert_that(field_names, equal_to(["apple", "mango", "zebra"]))


def test_sort_schema_defaults_to_false():
    """Test that sort_schema defaults to False (preserves definition order)."""
    Root = g.ObjectType("Root", fields=(
        g.field("zebra", g.String),
        g.field("apple", g.String),
    ))

    # Call without sort_schema parameter
    schema = create_graphql_schema(query_type=Root)
    field_names = list(schema.graphql_schema.query_type.fields.keys())

    # Should preserve definition order (not sorted)
    assert_that(field_names, equal_to(["zebra", "apple"]))


def test_types_are_sorted_in_type_map_when_sort_schema_is_true():
    """Test that type names in the type map are sorted alphabetically."""
    TypeZ = g.ObjectType("TypeZ", fields=(g.field("value", g.String),))
    TypeA = g.ObjectType("TypeA", fields=(g.field("value", g.String),))
    TypeM = g.ObjectType("TypeM", fields=(g.field("value", g.String),))

    Root = g.ObjectType("Root", fields=(
        g.field("z", TypeZ),
        g.field("a", TypeA),
        g.field("m", TypeM),
    ))

    schema = create_graphql_schema(query_type=Root, sort_schema=True, types=(TypeZ, TypeA, TypeM))

    # Filter out built-in types (those starting with __)
    custom_type_names = [
        name for name in schema.graphql_schema.type_map.keys()
        if not name.startswith("__")
    ]

    # Check that non-introspection types (built-ins and custom object types)
    # appear in sorted order: Boolean, Root, String, TypeA, TypeM, TypeZ
    assert_that(custom_type_names, contains_exactly(
        "Boolean", "Root", "String", "TypeA", "TypeM", "TypeZ"
    ))
