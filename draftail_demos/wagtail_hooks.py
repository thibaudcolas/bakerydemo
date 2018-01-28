from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext, ungettext

import wagtail.admin.rich_text.editors.draftail.features as draftail_features
from wagtail.admin.rich_text import HalloPlugin
from wagtail.core import hooks
from wagtail.core.whitelist import allow_without_attributes

from .rich_text import ContentstateStrikethroughConversionRule


@hooks.register('register_rich_text_features')
def register_strikethrough_feature(features):
    features.default_features.append('strikethrough')

    features.register_converter_rule(
        'contentstate', 'strikethrough', ContentstateStrikethroughConversionRule)

    features.register_editor_plugin(
        'draftail', 'strikethrough', draftail_features.InlineStyleFeature({
            'type': 'STRIKETHROUGH',
            'label': 'S',
            # TODO This isn't possible right now due to a bug in Wagtail - needs fixing.
            # 'icon': 'M1024 512v64h-234.506c27.504 38.51 42.506 82.692 42.506 128 0 70.878-36.66 139.026-100.58 186.964-59.358 44.518-137.284 69.036-219.42 69.036-82.138 0-160.062-24.518-219.42-69.036-63.92-47.938-100.58-116.086-100.58-186.964h128c0 69.382 87.926 128 192 128s192-58.618 192-128c0-69.382-87.926-128-192-128h-512v-64h299.518c-2.338-1.654-4.656-3.324-6.938-5.036-63.92-47.94-100.58-116.086-100.58-186.964s36.66-139.024 100.58-186.964c59.358-44.518 137.282-69.036 219.42-69.036 82.136 0 160.062 24.518 219.42 69.036 63.92 47.94 100.58 116.086 100.58 186.964h-128c0-69.382-87.926-128-192-128s-192 58.618-192 128c0 69.382 87.926 128 192 128 78.978 0 154.054 22.678 212.482 64h299.518z',
            'description': ugettext('Strikethrough'),
        })
    )


@hooks.register('construct_whitelister_element_rules')
def whitelister_strikethrough_feature():
    return {
        's': allow_without_attributes,
    }
