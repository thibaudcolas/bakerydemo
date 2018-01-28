import wagtail.admin.rich_text.editors.draftail.features as draftail_features
from wagtail.admin.rich_text.converters.html_to_contentstate import InlineStyleElementHandler
from wagtail.core import hooks
from wagtail.core.whitelist import allow_without_attributes


@hooks.register('register_rich_text_features')
def register_strikethrough_feature(features):
    # We enable a new feature called strikethrough.
    features.default_features.append('strikethrough')

    # We define how the feature is to be converted from Wagtail's DB format to the editor's format.
    features.register_converter_rule(
        # In this case, `contentstate` corresponds to the Draftail editor, and `strikethrough` is the feature name.
        'contentstate', 'strikethrough', {
            # From DB HTML to Draft.js content for Draftail.
            'from_database_format': {
                # Convert `<s>` tags into STRIKETHROUGH inline styles.
                's': InlineStyleElementHandler('STRIKETHROUGH'),
            },
            # From Draft.js content for Draftail to DB HTML.
            'to_database_format': {
                # Convert STRIKETHROUGH inline styles into `<s>` tags.
                'style_map': {'STRIKETHROUGH': 's'}
            }
        })

    # We define how the editor will implement the strikethrough feature.
    features.register_editor_plugin(
        # The editor is `draftail`, and the feature is `strikethrough`, and it's a Draftail "inline style" feature.
        'draftail', 'strikethrough', draftail_features.InlineStyleFeature({
            # This should be the same as the uppercase identifiers above.
            'type': 'STRIKETHROUGH',
            # This will be displayed in the toolbar.
            'label': 'S',
            # TODO This isn't possible right now due to a bug in Wagtail - needs fixing.
            # 'icon': 'M1024 512v64h-234.506c27.504 38.51 42.506 82.692 42.506 128 0 70.878-36.66 139.026-100.58 186.964-59.358 44.518-137.284 69.036-219.42 69.036-82.138 0-160.062-24.518-219.42-69.036-63.92-47.938-100.58-116.086-100.58-186.964h128c0 69.382 87.926 128 192 128s192-58.618 192-128c0-69.382-87.926-128-192-128h-512v-64h299.518c-2.338-1.654-4.656-3.324-6.938-5.036-63.92-47.94-100.58-116.086-100.58-186.964s36.66-139.024 100.58-186.964c59.358-44.518 137.282-69.036 219.42-69.036 82.136 0 160.062 24.518 219.42 69.036 63.92 47.94 100.58 116.086 100.58 186.964h-128c0-69.382-87.926-128-192-128s-192 58.618-192 128c0 69.382 87.926 128 192 128 78.978 0 154.054 22.678 212.482 64h299.518z',
            # This will be displayed in the toolbar tooltip - optional.
            'description': 'Strikethrough',
        })
    )


@hooks.register('construct_whitelister_element_rules')
def whitelister_strikethrough_feature():
    return {
        # Finally, we also need to configure Wagtail so it keeps the `s` tag when storing HTML in the DB.
        's': allow_without_attributes,
    }
