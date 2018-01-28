from wagtail.admin.rich_text.converters.html_to_contentstate import InlineStyleElementHandler

ContentstateStrikethroughConversionRule = {
    # When retrieving Draft.js content from storage.
    'from_database_format': {
        # Convert `<s>` tags into STRIKETHROUGH inline styles.
        's': InlineStyleElementHandler('STRIKETHROUGH'),
    },
    # When converting Draft.js content for storage.
    'to_database_format': {
        # Convert STRIKETHROUGH inline styles into `<s>` tags.
        'style_map': {'STRIKETHROUGH': 's'}
    }
}
