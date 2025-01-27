import wagtail.admin.rich_text.editors.draftail.features as draftail_features
from wagtail.admin.rich_text.converters.html_to_contentstate import (
    InlineStyleElementHandler,
)
from wagtail import hooks


# 1. Use the register_rich_text_features hook.
@hooks.register("register_rich_text_features")
def register_ref_footnotes_style_feature(features):
    """
    Registering the `ref-footnotes-style` feature, which uses the `REF_FOOTNOTES_STYLE` Draft.js inline style type,
    and is stored as HTML with a `<ref-style>` tag.
    """
    feature_name = "ref-footnotes-style"
    type_ = "REF_FOOTNOTES_STYLE"
    tag = "ref-style"

    # 2. Configure how Draftail handles the feature in its toolbar.
    control = {
        "type": type_,
        "label": "Ref (S)",
        "description": "Ref footnote (style)",
        "style": {"background": "var(--ref-footnotes-style)"},
    }

    # 3. Call register_editor_plugin to register the configuration for Draftail.
    features.register_editor_plugin(
        "draftail", feature_name, draftail_features.InlineStyleFeature(control)
    )

    # 4.configure the content transform from the DB to the editor and back.
    db_conversion = {
        "from_database_format": {tag: InlineStyleElementHandler(type_)},
        "to_database_format": {"style_map": {type_: tag}},
    }

    # 5. Call register_converter_rule to register the content transformation conversion.
    features.register_converter_rule("contentstate", feature_name, db_conversion)

    # 6. (optional) Add the feature to the default features list to make it available
    # on rich text fields that do not specify an explicit 'features' list
    features.default_features.append(feature_name)


@hooks.register("insert_global_admin_css")
def editor_css():
    return """<link rel="stylesheet" href="/static/ref_footnotes_style.css">"""
