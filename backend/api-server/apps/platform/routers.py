from fastapi import APIRouter
from .api.news import news_router, public_news_router
from .api.setup import setup_router
from .api.setting import setting_router
from .api.chat import chat_router
from .api.public_chat import public_chat_router
from .api.sites import sites_router
from .api.public import public_router

app_platform_router = APIRouter()
app_platform_router.include_router(news_router, prefix='/platform')
app_platform_router.include_router(setting_router, prefix='/platform')
app_platform_router.include_router(setup_router, prefix='/platform')
app_platform_router.include_router(chat_router, prefix='/platform')
app_platform_router.include_router(public_news_router, prefix='/public')
app_platform_router.include_router(setting_router, prefix='/public')
app_platform_router.include_router(public_chat_router, prefix='/public/chat')
app_platform_router.include_router(sites_router, prefix='/admin')
app_platform_router.include_router(public_router, prefix='/public')
