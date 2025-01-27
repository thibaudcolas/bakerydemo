from bs4 import BeautifulSoup


# footnote tags - see docstring for Footnotary
REF_TAGS = [("&lt;ref&gt;", "<ref>"), ("&lt;/ref&gt;", "</ref>")]


class Footnotary:
    """Turn <ref>footnotes</ref> in page.body into links and notes with backlinks

    IMPORTANT: Footnotes <ref> tags are stored as entity references (&lt;/ref&gt;).
    This way they are visible to the user in the UI but are hidden from Wagtail's
    RichTextBlock editor and parser.
    """

    @staticmethod
    def update_footnotes(page, fields, request=None, save=True):
        """Copy Mediawiki-style <ref> footnotes from page body to a Footnotes block

        Run in after_create_page and after_edit_page hooks.

        save=False is used in migrations.Articles.import_article to process
        footnotes before Articles' initial save/attachement to parent Page.
        """
        # smoosh HTML from the paragraph blocks into one string
        html = "\n".join(
            [
                block["value"]
                for block in page.body.raw_data
                if block["type"] == "paragraph_block"
            ]
        )
        # the <ref> tags might have been escaped so fix them
        for broken, fixed in REF_TAGS:
            html = html.replace(broken, fixed)
        # extract each <ref></ref> tag and build HTML
        soup = BeautifulSoup(html, features="html5lib")
        footnotes = "\n".join([str(ref) for ref in soup.find_all("ref")])
        # replace the old footnotes block
        page.footnotes = footnotes
        # save the page
        if save:
            new_revision = page.save_revision()
        if save and page.live:
            # page has been created and published at the same time,
            # so ensure that the updated title is on the published version too
            new_revision.publish()

    @staticmethod
    def prep_footnotes(page, fields, request):
        """Prep <ref>footnotes</ref> in the text for display

        Run in before_serve_page hooks.
        """
        n = 1
        for block in page.body:
            if block.block_type == "paragraph":
                html, n = Footnotary._rewrite_body_html(str(block.value), n)
                block.value.source = html
        page.footnotes = Footnotary._rewrite_footnotes_html(page.footnotes)

    @staticmethod
    def _rewrite_body_html(html, n):
        """Replace <ref>footnotes</ref> in page body with links to footnotes

        BEFORE
            <ref>Footnote text</ref>
        AFTER
            <sup class="reference" id="cite_ref-1">
              <a class="" href="#cite_note-1">
                [1]
              </a>
            </sup>
        """
        # <ref> tags might have been escaped so fix them
        for broken, fixed in REF_TAGS:
            html = html.replace(broken, fixed)
        soup = BeautifulSoup(html, features="html5lib")
        # remove <head> and <body>
        soup.html.unwrap()
        soup.head.unwrap()
        soup.body.unwrap()
        # rewrite <ref> tags as <li> with backlinks
        for item in soup.find_all("ref"):
            ref_name = f"cite_ref-{n}"
            note_name = f"cite_note-{n}"
            # insert <a name> before
            anchor = soup.new_tag("a")
            anchor["name"] = ref_name
            item.insert_before(anchor)
            # rewrite <ref> as <a href>
            item.name = "a"
            item["href"] = f"#{note_name}"
            item.string = f"[{n}]"
            # increment
            n += 1
        return str(soup), n

    @staticmethod
    def _rewrite_footnotes_html(html):
        """Replace <refs> in footnotes field with <li>notes</li> and backlinks

        BEFORE
            <ref>First footnote text</ref>
            <ref>Second footnote text</ref>
        AFTER
            <ol class="references">
              <li id="cite_note-1">
                <span class="mw-cite-backlink">
                  <a class="" href="#cite_ref-1">↑</a>
                </span>
                <span class="reference-text">...</span>
              </li>
              ...
            </ol>
        """
        if not html:
            return ""
        soup = BeautifulSoup(html, features="html5lib")
        # remove <head> and <body>
        soup.head.unwrap()
        soup.body.unwrap()
        # rename <html> to <ol>
        soup.html.name = "ol"
        soup.ol["class"] = "references"
        # rewrite <ref> tags as <li> with backlinks
        for n, item in enumerate(soup.find_all("ref"), start=1):
            ref_name = f"cite_ref-{n}"
            note_name = f"cite_note-{n}"
            # insert <a name> before
            anchor = soup.new_tag("a")
            anchor["name"] = note_name
            item.insert_before(anchor)
            # rewrite <ref> as <a href>
            item.name = "li"
            item["id"] = note_name
            # insert backlink
            item.insert(0, " ")
            backlink = soup.new_tag("a")
            backlink["href"] = f"#{ref_name}"
            backlink.string = "↑"
            item.insert(0, backlink)
        return str(soup)
