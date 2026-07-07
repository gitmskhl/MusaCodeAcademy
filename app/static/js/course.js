(function () {
    const course = {
        title: 'Python for Beginners',
        description: 'Learn Python from scratch with theory, examples and practical exercises.',
        progress: 42,
        sections: [
            {
                id: 'section-introduction',
                number: 1,
                title: 'Introduction',
                lessons: [
                    {
                        id: 'lesson-what-is-python',
                        number: 1,
                        title: 'What is Python',
                        status: 'completed',
                    },
                    {
                        id: 'lesson-installing-python',
                        number: 2,
                        title: 'Installing Python',
                        status: 'current',
                    },
                    {
                        id: 'lesson-first-program',
                        number: 3,
                        title: 'Your first Python program',
                        status: 'locked',
                    },
                ],
            },
            {
                id: 'section-core-syntax',
                number: 2,
                title: 'Core Syntax',
                lessons: [
                    {
                        id: 'lesson-variables',
                        number: 1,
                        title: 'Variables and data types',
                        status: 'locked',
                    },
                    {
                        id: 'lesson-operators',
                        number: 2,
                        title: 'Operators and expressions',
                        status: 'locked',
                    },
                    {
                        id: 'lesson-conditions',
                        number: 3,
                        title: 'Conditional statements',
                        status: 'locked',
                    },
                ],
            },
            {
                id: 'section-practice',
                number: 3,
                title: 'Practice and Exercises',
                lessons: [
                    {
                        id: 'lesson-loops',
                        number: 1,
                        title: 'Loops in practice',
                        status: 'locked',
                    },
                    {
                        id: 'lesson-functions',
                        number: 2,
                        title: 'Writing reusable functions',
                        status: 'locked',
                    },
                    {
                        id: 'lesson-mini-project',
                        number: 3,
                        title: 'Build a small command line project',
                        status: 'locked',
                    },
                ],
            },
        ],
    };

    const statusMap = {
        completed: {
            className: 'lesson-row--completed',
            icon: '\u2713',
            label: 'completed',
        },
        current: {
            className: 'lesson-row--current',
            icon: '\u25b6',
            label: 'current lesson',
        },
        locked: {
            className: 'lesson-row--locked',
            icon: '\ud83d\udd12',
            label: 'locked',
        },
    };

    const elements = {
        title: document.querySelector('[data-course-title]'),
        description: document.querySelector('[data-course-description]'),
        progressMeter: document.querySelector('[data-progress-meter]'),
        progressPercent: document.querySelector('[data-progress-percent]'),
        sections: document.querySelector('[data-sections]'),
    };

    const createProgressSegments = (progress) => {
        const segmentCount = 10;
        const filledSegments = Math.round((progress / 100) * segmentCount);
        const fragment = document.createDocumentFragment();

        for (let index = 0; index < segmentCount; index += 1) {
            const segment = document.createElement('span');
            segment.className = 'course-progress__segment';

            if (index < filledSegments) {
                segment.classList.add('is-filled');
            }

            fragment.append(segment);
        }

        return fragment;
    };

    const createLessonRow = (lesson) => {
        const status = statusMap[lesson.status] || statusMap.locked;
        const row = document.createElement('button');
        const number = document.createElement('span');
        const title = document.createElement('span');
        const icon = document.createElement('span');

        row.type = 'button';
        row.className = `lesson-row ${status.className}`;
        row.dataset.lessonId = lesson.id;
        row.setAttribute('aria-label', `Lesson ${lesson.number}. ${lesson.title}, ${status.label}`);

        if (lesson.status === 'locked') {
            row.setAttribute('aria-disabled', 'true');
        }

        number.className = 'lesson-row__number';
        number.textContent = `Lesson ${lesson.number}.`;

        title.className = 'lesson-row__title';
        title.textContent = lesson.title;

        icon.className = 'lesson-row__status';
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = status.icon;

        row.append(number, title, icon);
        row.addEventListener('click', () => {
            console.log(lesson.id);
        });

        return row;
    };

    const createSectionCard = (section, isOpen) => {
        const card = document.createElement('article');
        const toggle = document.createElement('button');
        const icon = document.createElement('span');
        const heading = document.createElement('span');
        const count = document.createElement('span');
        const body = document.createElement('div');
        const inner = document.createElement('div');
        const lessonList = document.createElement('div');
        const contentId = `${section.id}-lessons`;

        card.className = 'section-card';
        card.classList.toggle('is-open', isOpen);

        toggle.type = 'button';
        toggle.className = 'section-card__toggle';
        toggle.setAttribute('aria-expanded', String(isOpen));
        toggle.setAttribute('aria-controls', contentId);

        icon.className = 'section-card__icon';
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = '\u203a';

        heading.className = 'section-card__heading';
        heading.textContent = `Section ${section.number}. ${section.title}`;

        count.className = 'section-card__count';
        count.textContent = `${section.lessons.length} lessons`;

        body.className = 'section-card__body';
        body.id = contentId;

        inner.className = 'section-card__inner';
        lessonList.className = 'lesson-list';

        section.lessons.forEach((lesson) => {
            lessonList.append(createLessonRow(lesson));
        });

        toggle.append(icon, heading, count);
        inner.append(lessonList);
        body.append(inner);
        card.append(toggle, body);

        toggle.addEventListener('click', () => {
            const nextOpenState = !card.classList.contains('is-open');
            card.classList.toggle('is-open', nextOpenState);
            toggle.setAttribute('aria-expanded', String(nextOpenState));
        });

        return card;
    };

    const render = () => {
        document.title = course.title;
        elements.title.textContent = course.title;
        elements.description.textContent = course.description;
        elements.progressPercent.textContent = `${course.progress}%`;
        elements.progressMeter.setAttribute('aria-valuenow', String(course.progress));
        elements.progressMeter.replaceChildren(createProgressSegments(course.progress));

        const fragment = document.createDocumentFragment();
        course.sections.forEach((section, index) => {
            fragment.append(createSectionCard(section, index === 0));
        });
        elements.sections.replaceChildren(fragment);
    };

    document.addEventListener('DOMContentLoaded', render);
})();
