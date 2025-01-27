(() => {
  const React = window.React;
  const { registerPlugin } = window.draftail;

  const FOOTNOTES_REFS = /<\/?ref>/g;

  const refFootnoteTagDecorator = {
    type: "ref-footnotes-markers",

    strategy: (block, callback) => {
      const text = block.getText();
      let matches;
      while ((matches = FOOTNOTES_REFS.exec(text)) !== null) {
        callback(matches.index, matches.index + matches[0].length);
      }
    },

    component: ({ children }) => {
      return React.createElement("span", {
        style: {
          color: 'var(--w-color-text-link-default)',
          fontFamily: 'var(--w-font-mono)',
          opacity: 0.7,
        },
        title: 'Footnote contents',
      }, children);
    },
  }

  registerPlugin(refFootnoteTagDecorator, 'decorators');
})();

(() => {
  const React = window.React;
  const { registerPlugin } = window.draftail;
  const { EditorState, Modifier } = window.DraftJS;
  const { ToolbarButton } = window.Draftail;

  /**
 * Returns collection of currently selected blocks.
 * See https://github.com/jpuri/draftjs-utils/blob/e81c0ae19c3b0fdef7e0c1b70d924398956be126/js/block.js#L19.
 */
const getSelectedBlocksList = (editorState) => {
  const selectionState = editorState.getSelection();
  const content = editorState.getCurrentContent();
  const startKey = selectionState.getStartKey();
  const endKey = selectionState.getEndKey();
  const blockMap = content.getBlockMap();
  const blocks = blockMap
    .toSeq()
    .skipUntil((_, k) => k === startKey)
    .takeUntil((_, k) => k === endKey)
    .concat([[endKey, blockMap.get(endKey)]]);
  return blocks.toList();
};

  /**
 * Returns the currently selected text in the editor.
 * See https://github.com/jpuri/draftjs-utils/blob/e81c0ae19c3b0fdef7e0c1b70d924398956be126/js/block.js#L106.
 */
  const getSelectionText = (editorState) => {
    const selection = editorState.getSelection();
    let start = selection.getAnchorOffset();
    let end = selection.getFocusOffset();
    const selectedBlocks = getSelectedBlocksList(editorState);

    if (selection.getIsBackward()) {
      const temp = start;
      start = end;
      end = temp;
    }

    let selectedText = '';
    for (let i = 0; i < selectedBlocks.size; i += 1) {
      const blockStart = i === 0 ? start : 0;
      const blockEnd =
        i === selectedBlocks.size - 1
          ? end
          : selectedBlocks.get(i).getText().length;
      selectedText += selectedBlocks.get(i).getText().slice(blockStart, blockEnd);
    }

    return selectedText;
  };


  const FootnotesInserter = ({ getEditorState, onChange }) => {
    const insertFootnotesContent = () => {
      const editorState = getEditorState();
      const selection = editorState.getSelection();
      let content = editorState.getCurrentContent();

      if (selection.isCollapsed()) {
        content = Modifier.insertText(content, selection, '<ref>footnote content</ref>');
      } else {
        const newText = `<ref>${getSelectionText(editorState)}</ref>`;
        content = Modifier.replaceText(content, selection, newText);
      }
      onChange(EditorState.push(editorState, content, 'insert-characters'));
    };

    return React.createElement(ToolbarButton, {
      name: "REF_INSERT",
      label: "<ref>",
      description: "Footnote reference",
      onClick: insertFootnotesContent,
    });
  }

  const refFootnoteTagControl = {
    type: 'ref-footnotes-markers',
    inline: FootnotesInserter,
  }

  registerPlugin(refFootnoteTagControl, 'controls');
})();
