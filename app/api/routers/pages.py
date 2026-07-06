from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html"
    )


@router.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html"
    )
    

@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html"
    )
    

@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_page(request: Request):
    return templates.TemplateResponse(
        request,
        "admin.html"
    )
    
@router.get("/admin/courses/create", response_class=HTMLResponse, include_in_schema=False)
async def admin_create_course_page(request: Request):
    return templates.TemplateResponse(
        request,
        "create_course.html"
    )
  
@router.get("/admin/courses/{course_id}/edit", response_class=HTMLResponse, include_in_schema=False)
async def admin_edit_course_page(request: Request, course_id: int):
    return templates.TemplateResponse(
        request,
        "edit_course.html", {"course_id": course_id}
    )  
    
@router.get("/admin/courses/{course_id}", response_class=HTMLResponse, include_in_schema=False)
async def admin_course_page(request: Request, course_id: int):
    return templates.TemplateResponse(
        request,
        "course_sections.html", {"course_id": course_id}
    )


@router.get("/admin/lessons/{lesson_id}", response_class=HTMLResponse, include_in_schema=False)
async def admin_lesson_steps_page(request: Request, lesson_id: int):
    return templates.TemplateResponse(
        request,
        "lesson_steps.html", {"lesson_id": lesson_id}
    )


@router.get("/admin/steps/{step_id}", response_class=HTMLResponse, include_in_schema=False)
async def admin_step_editor_page(request: Request, step_id: int):
    return templates.TemplateResponse(
        request,
        "step_editor.html", {"step_id": step_id}
    )


@router.get("/{course_slug}/steps/{step_id}", response_class=HTMLResponse, include_in_schema=False)
async def step_viewer_page(
    request: Request,
    course_slug: str,
    step_id: int,
):
    return templates.TemplateResponse(
        request,
        "step_viewer.html",
        context={
            "request": request,
            "course_slug": course_slug,
            "step_id": step_id,
        },
    )


@router.get(
    "/{course_slug}/lessons/{lesson_id}/steps",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def first_lesson_step_page(
    request: Request,
    course_slug: str,
    lesson_id: int,
):
    return templates.TemplateResponse(
        request,
        "lesson_step_redirect.html",
        context={
            "request": request,
            "course_slug": course_slug,
            "lesson_id": lesson_id,
        },
    )


@router.get('/{course_slug}/sections/{section_id}/lessons', response_class=HTMLResponse, include_in_schema=False)
async def section_lessons_page(
    request: Request,
    course_slug: str,
    section_id: int,
):
    return templates.TemplateResponse(
        request,
        "section_lessons.html",
        context={
            "request": request,
            "course_slug": course_slug,
            "section_id": section_id,
        },
    )
