const React = window.React;
const { Modifier, EditorState } = window.DraftJS;
const { DraftUtils, TooltipEntity } = window.draftail;
const { Icon } = window.wagtail.components;

const MAIL_ICON = React.createElement(Icon, { name: 'mail' });

class MergeTagSource extends React.Component {
  componentDidMount() {
    const { editorState, entityType, onComplete } = this.props;

    const content = editorState.getCurrentContent();
    const selection = editorState.getSelection();

    const demoTags = ['CAMPAIGN_UID', 'ARCHIVE', 'BRAND:LOGO', 'REWARDS', 'REWARDS_TEXT'];
    const randomTag = demoTags[Math.floor(Math.random() * demoTags.length)];

    // Uses the Draft.js API to create a new entity with the right data.
    const contentWithEntity = content.createEntity(
      entityType.type,
      'IMMUTABLE',
      {
        tag: randomTag,
      },
    );
    const entityKey = contentWithEntity.getLastCreatedEntityKey();

    // We also add some text for the entity to be activated on.
    const text = `*|${randomTag}|*`;

    const newContent = Modifier.replaceText(
      content,
      selection,
      text,
      null,
      entityKey,
    );
    const nextState = EditorState.push(
      editorState,
      newContent,
      'insert-characters',
    );

    onComplete(nextState);
  }

  render() {
    return null;
  }
}

const MergeTag = ({ children, entityKey, contentState, getEditorState, setEditorState,  }) => {
  const data = contentState.getEntity(entityKey).getData();

  const onRemove = () => {
    let editorState = getEditorState();
    let content = editorState.getCurrentContent();

    const selection = DraftUtils.getEntitySelection(editorState, entityKey);
    content = Modifier.removeRange(content, selection, 'backward');

    editorState = EditorState.push(editorState, content, 'remove-range');
    setEditorState(editorState);
  }

  return React.createElement(
      TooltipEntity,
      {
          entityKey,
          contentState,
          onEdit,
          onRemove,
          icon: MAIL_ICON,
          label: 'Merge tag',
          url: 'test',
      },
      children,
  );
};

window.draftail.registerPlugin({
  type: 'MERGE_TAG',
  source: MergeTagSource,
  decorator: MergeTag,
}, 'entityTypes');
