const mockCourses = {
    'python-for-basics': {
        title: 'Python для начинающих',
        description:
            'Изучите Python с нуля. Научитесь писать программы, работать со строками, списками, функциями и создадите первые собственные проекты.',
        lessonsCount: 32,
        sectionsCount: 8,
        level: 'Начинающий',
        price: 'Бесплатно',
        outcomes: [
            'Переменные',
            'Условия',
            'Циклы',
            'Функции',
            'Списки',
            'Словари',
            'Файлы',
            'Основы ООП',
        ],
        program: [
            {
                title: 'Введение',
                lessons: ['Что такое Python', 'Первая программа', 'Переменные'],
            },
            {
                title: 'Условия',
                lessons: ['if', 'elif', 'Практика'],
            },
            {
                title: 'Циклы',
                lessons: ['while', 'for', 'Вложенные циклы', 'Практические задачи'],
            },
            {
                title: 'Коллекции',
                lessons: ['Списки', 'Словари', 'Кортежи', 'Методы коллекций'],
            },
            {
                title: 'Функции',
                lessons: ['Создание функций', 'Аргументы', 'Возвращаемые значения'],
            },
            {
                title: 'Файлы и проекты',
                lessons: ['Чтение файлов', 'Запись файлов', 'Первый мини-проект'],
            },
            {
                title: 'Основы ООП',
                lessons: ['Классы', 'Объекты', 'Методы', 'Финальная практика'],
            },
        ],
    },
};

const fallbackCourse = mockCourses['python-for-basics'];

const elements = {
    root: document.querySelector('[data-course-page]'),
    title: document.querySelector('[data-course-title]'),
    description: document.querySelector('[data-course-description]'),
    outcomes: document.querySelector('[data-course-outcomes]'),
    program: document.querySelector('[data-course-program]'),
    lessonsCount: document.querySelector('[data-course-lessons-count]'),
    sectionsCount: document.querySelector('[data-course-sections-count]'),
    level: document.querySelector('[data-course-level]'),
    price: document.querySelector('[data-course-price]'),
};

const getCourseSlug = () => {
    const templateSlug = elements.root?.dataset.courseSlug?.trim();
    if (templateSlug) {
        return templateSlug;
    }

    const [, slug] = window.location.pathname.match(/^\/([^/]+)\/?$/) || [];
    return slug ? decodeURIComponent(slug) : 'python-for-basics';
};

const createOutcomeItem = (outcome) => {
    const item = document.createElement('li');
    item.textContent = outcome;
    return item;
};

const createLessonItem = (lesson) => {
    const item = document.createElement('li');
    item.textContent = lesson;
    return item;
};

const createProgramSection = (section, index) => {
    const item = document.createElement('article');
    const button = document.createElement('button');
    const title = document.createElement('span');
    const icon = document.createElement('span');
    const body = document.createElement('div');
    const inner = document.createElement('div');
    const list = document.createElement('ul');
    const contentId = `course-program-section-${index + 1}`;
    const isOpen = index === 0;

    item.className = 'course-accordion__item';
    item.classList.toggle('is-open', isOpen);

    button.className = 'course-accordion__button';
    button.type = 'button';
    button.setAttribute('aria-expanded', String(isOpen));
    button.setAttribute('aria-controls', contentId);

    icon.className = 'course-accordion__icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '\u25be';

    title.className = 'course-accordion__title';
    title.textContent = section.title;

    body.className = 'course-accordion__body';
    body.id = contentId;

    inner.className = 'course-accordion__inner';
    list.className = 'course-lessons';

    section.lessons.forEach((lesson) => {
        list.append(createLessonItem(lesson));
    });

    button.append(icon, title);
    inner.append(list);
    body.append(inner);
    item.append(button, body);

    button.addEventListener('click', () => {
        const nextOpenState = !item.classList.contains('is-open');
        item.classList.toggle('is-open', nextOpenState);
        button.setAttribute('aria-expanded', String(nextOpenState));
    });

    return item;
};

const renderCourse = (course) => {
    document.title = `${course.title} | Musa Code Academy`;
    elements.title.textContent = course.title;
    elements.description.textContent = course.description;
    elements.lessonsCount.textContent = course.lessonsCount;
    elements.sectionsCount.textContent = course.sectionsCount;
    elements.level.textContent = course.level;
    elements.price.textContent = course.price;

    elements.outcomes.replaceChildren(...course.outcomes.map(createOutcomeItem));
    elements.program.replaceChildren(...course.program.map(createProgramSection));
};

document.addEventListener('DOMContentLoaded', () => {
    const course = mockCourses[getCourseSlug()] || fallbackCourse;
    renderCourse(course);
});
