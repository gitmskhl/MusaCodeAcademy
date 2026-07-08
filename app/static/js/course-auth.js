const TOKEN_KEY = 'musa_code_academy_token';
const ENROLLED_COURSES_KEY = 'musa_code_academy_enrolled_courses';

const currentUrl = () =>
    `${window.location.pathname}${window.location.search}${window.location.hash}`;

export const redirectToLogin = () => {
    const params = new URLSearchParams({ next: currentUrl() });
    window.location.replace(`/login?${params.toString()}`);
};

export const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ENROLLED_COURSES_KEY);
    window.location.replace('/login');
};

export const requireToken = () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
        redirectToLogin();
        throw new Error('authentication-required');
    }
    return token;
};

export const authFetch = async (input, init = {}) => {
    const token = requireToken();
    const headers = new Headers(init.headers || {});
    headers.set('Authorization', `Bearer ${token}`);

    const response = await fetch(input, { ...init, headers });
    if (response.status === 401) {
        localStorage.removeItem(TOKEN_KEY);
        redirectToLogin();
        throw new Error('authentication-required');
    }
    return response;
};

export const requireCurrentUser = async () => {
    const response = await authFetch('/api/users/me');
    if (!response.ok) {
        throw new Error('authentication-check-failed');
    }
    return response.json();
};
