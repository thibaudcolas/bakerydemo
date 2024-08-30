from draftjs_exporter.dom import DOM
from wagtail.admin.rich_text.editors.draftail.features import (
    InlineStyleFeature,
    EntityFeature,
)
from wagtail.admin.rich_text.converters.html_to_contentstate import (
    InlineStyleElementHandler,
    InlineEntityElementHandler,
)
from wagtail import hooks


@hooks.register("register_rich_text_features")
def register_math_text(features):
    features.default_features.append("blockquote")
    features.default_features.append("superscript")
    features.default_features.append("subscript")
    features.default_features.append("math_text")

    features.register_converter_rule(
        "contentstate",
        "math_text",
        {
            "from_database_format": {
                'span[class="math-text"]': InlineStyleElementHandler("MATH_TEXT"),
            },
            "to_database_format": {
                "style_map": {
                    "MATH_TEXT": {
                        "element": "span",
                        "props": {"class": "math-text"},
                    },
                }
            },
        },
    )

    features.register_editor_plugin(
        "draftail",
        "math_text",
        InlineStyleFeature(
            {
                "type": "MATH_TEXT",
                "label": "𝚳",
                "description": "Mathematical text",
                "style": {
                    "fontFamily": "serif",
                    "fontStyle": "italic",
                },
            }
        ),
    )


class MergeTagElementHandler(InlineEntityElementHandler):
    mutability = "IMMUTABLE"

    def get_attribute_data(self, attrs):
        return {
            "tag": attrs.get("tag"),
            "linktype": "merge_tag",
        }


def merge_tag_entity_decorator(props):
    return DOM.create_element(
        "embed",
        {
            "tag": props.get("tag"),
            "embedtype": "merge_tag",
        },
        props["children"],
    )


@hooks.register("register_rich_text_features")
def register_merge_tag(features):
    features.default_features.append("merge_tag")

    features.register_converter_rule(
        "contentstate",
        "merge_tag",
        {
            "from_database_format": {
                'embed[embedtype="merge_tag"]': MergeTagElementHandler("MERGE_TAG"),
            },
            "to_database_format": {
                "entity_decorators": {
                    "MERGE_TAG": merge_tag_entity_decorator,
                }
            },
        },
    )

    features.register_editor_plugin(
        "draftail",
        "merge_tag",
        EntityFeature(
            {
                "type": "MERGE_TAG",
                "label": "MC",
                "description": "Mailchimp Merge tag",
            },
            js=["rich_text_demos/merge-tag.js"],
        ),
    )
