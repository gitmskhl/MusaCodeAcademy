import {
    basicSetup,
    Compartment,
    cpp,
    EditorState,
    EditorView,
    indentWithTab,
    java,
    javascript,
    keymap,
    placeholder,
    python,
    selectLineDown,
    selectLineUp,
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

const lightTheme = EditorView.theme({
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
    '.cm-activeLine, .cm-activeLineGutter': {
        backgroundColor: '#eef4ff',
    },
    '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
        backgroundColor: '#add6ff',
    },
    '&:not(.cm-focused) > .cm-scroller > .cm-selectionLayer .cm-selectionBackground': {
        backgroundColor: '#dce8f6',
    },
});

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
    let changeHandler = onChange;
    let isEditable = editable;
    let activeLanguage = language.trim().toLowerCase();

    const editableExtensions = (nextEditable) => [
        EditorState.readOnly.of(!nextEditable),
        EditorView.editable.of(nextEditable),
        EditorView.contentAttributes.of({
            'aria-label': 'Code',
            'aria-readonly': String(!nextEditable),
            spellcheck: 'false',
        }),
    ];

    const state = EditorState.create({
        doc: document,
        extensions: [
            basicSetup,
            keymap.of([indentWithTab, ...desktopSelectionKeymap]),
            placeholder('Write or paste code…'),
            languageConfig.of(getLanguageExtension(language)),
            editableConfig.of(editableExtensions(editable)),
            lightTheme,
            EditorView.updateListener.of((update) => {
                if (update.docChanged) {
                    changeHandler(update.state.doc.toString());
                }
            }),
        ],
    });
    const view = new EditorView({ state, parent });

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
        destroy: () => view.destroy(),
    };
};
