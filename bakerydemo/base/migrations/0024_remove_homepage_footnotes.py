# Generated by Django 5.0.11 on 2025-01-27 15:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0023_homepage_footnotes_alter_formpage_body_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="homepage",
            name="footnotes",
        ),
    ]
