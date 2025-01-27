from wagtail.admin.rich_text.editors.draftail.features import Feature
from wagtail import hooks


class FootnotesMarkerFeature(Feature):
    """
    A feature which combines multiple types of editor customizations.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.js = ["ref_footnotes_markers.js"]

    def construct_options(self, options):
        if "decorators" not in options:
            options["decorators"] = []

        if "controls" not in options:
            options["controls"] = []

        options["decorators"].append({"type": "ref-footnotes-markers"})
        options["controls"].append({"type": "ref-footnotes-markers"})


@hooks.register("register_rich_text_features")
def register_ref_footnotes_markers_highlighter(features):
    feature_name = "ref-footnotes-markers"
    features.default_features.append(feature_name)

    features.register_editor_plugin(
        "draftail",
        feature_name,
        FootnotesMarkerFeature(),
    )


# Same as above but simpler – only shows footnotes text highlights.
# @hooks.register("register_rich_text_features")
# def register_ref_footnotes_markers_highlighter(features):
#     feature_name = "ref-footnotes-markers"
#     features.default_features.append(feature_name)

#     features.register_editor_plugin(
#         "draftail",
#         feature_name,
#         DecoratorFeature(
#             {
#                 "type": feature_name,
#             },
#             js=["ref_footnotes_markers.js"],
#         ),
#     )
