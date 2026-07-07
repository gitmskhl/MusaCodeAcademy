const courses = [
    {
        title: 'Python для начинающих',
        description: 'Основы синтаксиса, переменные, условия и первые небольшие программы.',
        progress: 62,
        action: 'Продолжить',
        href: '/python-basics',
    },
    {
        title: 'Основы HTML и CSS',
        description: 'Структура страницы, семантическая разметка и аккуратная стилизация интерфейсов.',
        progress: 34,
        action: 'Продолжить',
        href: '/html-css-basics',
    },
    {
        title: 'JavaScript: первый шаг',
        description: 'Типы данных, функции и работа с элементами страницы без лишней сложности.',
        progress: 0,
        action: 'Начать',
        href: '/javascript-first-step',
    },
];

const courseList = document.querySelector('[data-course-list]');

const createCourseCard = (course) => {
    const article = document.createElement('article');
    article.className = 'course-card';

    article.innerHTML = `
        <div>
            <h3>${course.title}</h3>
            <p>${course.description}</p>
        </div>
        <div class="course-card__progress" aria-label="Прогресс курса ${course.progress} процентов">
            <div class="course-card__meta">
                <span>Прогресс</span>
                <span>${course.progress}%</span>
            </div>
            <span class="course-card__bar">
                <span class="course-card__value" style="width: ${course.progress}%;"></span>
            </span>
        </div>
        <a class="course-card__button" href="${course.href}">${course.action}</a>
    `;

    return article;
};

courses.forEach((course) => {
    courseList.append(createCourseCard(course));
});
