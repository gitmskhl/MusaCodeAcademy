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
    onChange = () => {},
}) => {
    const languageConfig = new Compartment();
    const state = EditorState.create({
        doc: document,
        extensions: [
            basicSetup,
            keymap.of([indentWithTab]),
            placeholder('Write or paste code…'),
            languageConfig.of(getLanguageExtension(language)),
            lightTheme,
            EditorView.contentAttributes.of({
                'aria-label': 'Code',
                spellcheck: 'false',
            }),
            EditorView.updateListener.of((update) => {
                if (update.docChanged) {
                    onChange(update.state.doc.toString());
                }
            }),
        ],
    });
    const view = new EditorView({ state, parent });

    return {
        focus: () => view.focus(),
        setLanguage: (nextLanguage) => {
            view.dispatch({
                effects: languageConfig.reconfigure(
                    getLanguageExtension(nextLanguage)
                ),
            });
        },
        destroy: () => view.destroy(),
    };
};
