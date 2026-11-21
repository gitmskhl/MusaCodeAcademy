import {
    basicSetup,
    Compartment,
    cpp,
    EditorState,
    EditorView,
    HighlightStyle,
    indentWithTab,
    java,
    javascript,
    keymap,
    placeholder,
    python,
    selectLineDown,
    selectLineUp,
    syntaxHighlighting,
    tags,
} from '../../../vendor/codemirror.esm.js';

const languageExtensions = new Map([
    ['python', python],
    ['py', python],
    ['javascript', javascript],
    ['js', javascript],
    ['c++', cpp],
    ['cpp', cpp],
    ['cxx', cpp],
    ['java', java],
]);

const getLanguageExtension = (language) => {
    const languageSupport = languageExtensions.get(language.trim().toLowerCase());
    return languageSupport ? languageSupport() : [];
};

const editorStyles = {
    '&': {
        color: '#25272d',
        backgroundColor: '#fcfcfd',
        fontSize: '14px',
    },
    '.cm-content': {
        caretColor: '#2563eb',
        padding: '14px 0 18px',
    },
    '.cm-line': {
        padding: '0 14px',
    },
    '.cm-scroller': {
        fontFamily:
            '"JetBrains Mono", "Cascadia Code", "SFMono-Regular", Consolas, "Liberation Mono", monospace',
        lineHeight: '1.65',
    },
    '.cm-cursor, .cm-dropCursor': {
        borderLeftColor: '#2563eb',
        borderLeftWidth: '2px',
        marginLeft: '-1px',
    },
    '&.cm-focused .cm-cursor': {
        animation: 'cm-blink 1.15s ease-in-out infinite',
    },
    '.cm-gutters': {
        color: '#8a8e98',
        backgroundColor: '#f5f5f7',
        borderRight: '1px solid #e2e3e7',
    },
    '.cm-activeLine': {
        backgroundColor: 'transparent',
        boxShadow: 'inset 3px 0 0 rgba(37, 99, 235, 0.25)',
    },
    '.cm-activeLineGutter': {
        backgroundColor: '#eef4ff',
    },
    '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
        backgroundColor: '#add6ff',
    },
    '&:not(.cm-focused) > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
        backgroundColor: '#dce8f6',
    },
};

const lightTheme = EditorView.theme(editorStyles);
const darkTheme = EditorView.theme({
    ...editorStyles,
    '&': { color: '#edf2fc', backgroundColor: '#1d2432', fontSize: '14px' },
    '.cm-content': { ...editorStyles['.cm-content'], caretColor: '#a8c6ff' },
    '.cm-cursor, .cm-dropCursor': { ...editorStyles['.cm-cursor, .cm-dropCursor'], borderLeftColor: '#a8c6ff' },
    '.cm-gutters': { color: '#a4b2cb', backgroundColor: '#232d40', borderRight: '1px solid #43516b' },
    '.cm-activeLine': { backgroundColor: '#232d40', boxShadow: 'inset 3px 0 0 #789bd3' },
    '.cm-activeLineGutter': { backgroundColor: '#293e63' },
    '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': { backgroundColor: '#35568a' },
    '&:not(.cm-focused) > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': { backgroundColor: '#293e63' },
    '.cm-selectionMatch': { backgroundColor: '#35568a' },
    '.cm-matchingBracket': { color: '#a3e2b7', backgroundColor: '#1b3528' },
    '.cm-panels, .cm-tooltip': { color: '#edf2fc', backgroundColor: '#232d40', borderColor: '#43516b' },
    '.cm-searchMatch': { backgroundColor: '#5c4926' },
    '.cm-searchMatch-selected': { backgroundColor: '#796133' },
}, { dark: true });

const darkHighlighting = syntaxHighlighting(HighlightStyle.define([
    { tag: tags.keyword, color: '#c3a6ff' },
    { tag: [tags.name, tags.propertyName], color: '#edf2fc' },
    { tag: [tags.function(tags.variableName), tags.labelName], color: '#a8c6ff' },
    { tag: [tags.number, tags.bool, tags.null], color: '#f0d08d' },
    { tag: [tags.string, tags.regexp], color: '#a3e2b7' },
    { tag: tags.comment, color: '#a4b2cb', fontStyle: 'italic' },
    { tag: [tags.typeName, tags.className], color: '#90d6e8' },
    { tag: [tags.operator, tags.punctuation], color: '#bdc8dc' },
    { tag: tags.invalid, color: '#ffb8b3' },
]));

const desktopSelectionKeymap = [
    {
        key: 'Ctrl-Shift-ArrowUp',
        run: selectLineUp,
        preventDefault: true,
    },
    {
        key: 'Ctrl-Shift-ArrowDown',
        run: selectLineDown,
        preventDefault: true,
    },
];

export const createCodeEditorView = ({
    parent,
    document = '',
    language = '',
    editable = true,
    onChange = () => {},
}) => {
    const languageConfig = new Compartment();
    const editableConfig = new Compartment();
    const themeConfig = new Compartment();
    const themeWindow = parent.ownerDocument.defaultView;
    const themeExtensions = () => parent.ownerDocument.documentElement.dataset.theme === 'dark'
        ? [darkTheme, darkHighlighting] : lightTheme;
    let changeHandler = onChange;
    let isEditable = editable;
    let activeLanguage = language.trim().toLowerCase();

    const editableExtensions = (nextEditable) => [
        EditorState.readOnly.of(!nextEditable),
        EditorView.editable.of(nextEditable),
        EditorView.contentAttributes.of({
            'aria-label': 'Код',
            'aria-readonly': String(!nextEditable),
            spellcheck: 'false',
        }),
    ];

    const state = EditorState.create({
        doc: document,
        extensions: [
            basicSetup,
            keymap.of([indentWithTab, ...desktopSelectionKeymap]),
            placeholder('Напишите или вставьте код...'),
            languageConfig.of(getLanguageExtension(language)),
            editableConfig.of(editableExtensions(editable)),
            themeConfig.of(themeExtensions()),
            EditorView.updateListener.of((update) => {
                if (update.docChanged) {
                    changeHandler(update.state.doc.toString());
                }
            }),
        ],
    });
    const view = new EditorView({ state, parent });
    const updateTheme = () => view.dispatch({ effects: themeConfig.reconfigure(themeExtensions()) });
    themeWindow.addEventListener('academy:theme-change', updateTheme);

    return {
        focus: () => view.focus(),
        setDocument: (nextDocument) => {
            const currentDocument = view.state.doc.toString();
            if (nextDocument === currentDocument) {
                return;
            }
            view.dispatch({
                changes: {
                    from: 0,
                    to: view.state.doc.length,
                    insert: nextDocument,
                },
            });
        },
        setEditable: (nextEditable) => {
            if (nextEditable === isEditable) {
                return;
            }
            isEditable = nextEditable;
            view.dispatch({
                selection: view.state.selection,
                effects: editableConfig.reconfigure(
                    editableExtensions(nextEditable)
                ),
            });
        },
        setLanguage: (nextLanguage) => {
            const normalizedLanguage = nextLanguage.trim().toLowerCase();
            if (normalizedLanguage === activeLanguage) {
                return;
            }
            activeLanguage = normalizedLanguage;
            view.dispatch({
                effects: languageConfig.reconfigure(
                    getLanguageExtension(nextLanguage)
                ),
            });
        },
        setOnChange: (nextOnChange) => {
            changeHandler = nextOnChange;
        },
        destroy: () => {
            themeWindow.removeEventListener('academy:theme-change', updateTheme);
            view.destroy();
        },
    };
};
