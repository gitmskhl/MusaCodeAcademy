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
    },
    '.cm-content': {
        caretColor: '#635bdb',
        padding: '12px 0',
    },
    '.cm-cursor, .cm-dropCursor': {
        borderLeftColor: '#635bdb',
    },
    '.cm-gutters': {
        color: '#8a8e98',
        backgroundColor: '#f5f5f7',
        borderRight: '1px solid #e2e3e7',
    },
    '.cm-activeLine, .cm-activeLineGutter': {
        backgroundColor: '#f1f0ff',
    },
    '&.cm-focused .cm-selectionBackground, ::selection': {
        backgroundColor: '#dcd9ff',
    },
});

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
            keymap.of([indentWithTab]),
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
