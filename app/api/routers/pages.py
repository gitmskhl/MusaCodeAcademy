from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.api.dependencies import OnlyAdmin

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