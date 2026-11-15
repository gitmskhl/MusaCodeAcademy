const PREFIX = '# mca:function-test:v1\n';

const pythonLiteral = (value) => {
    if (value === null) return 'None';
    if (typeof value === 'boolean') return value ? 'True' : 'False';
    if (Array.isArray(value)) return `[${value.map(pythonLiteral).join(', ')}]`;
    return JSON.stringify(value);
};

export const describeFunctionTest = (input) => {
    if (!input.startsWith(PREFIX)) return null;
    try {
        const test = JSON.parse(input.slice(PREFIX.length));
        const call = `${test.function}(${test.args.map(pythonLiteral).join(', ')})`;
        return test.mode === 'print' ? call : `result = ${call}\nprint(result)`;
    } catch {
        return null;
    }
};
