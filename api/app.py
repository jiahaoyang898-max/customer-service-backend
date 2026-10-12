from contextlib import asynccontextmanager
from fastapi import FastAPI

from api.routers.chat_router import router
from infrastructure.database import init_db_engine, close_db_engine
from infrastructure.http_client import init_http_client, close_http_client
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    print("启动服务器...")
    print("初始化数据库链接资源")
    init_db_engine()
    init_http_client()
    yield
    await close_db_engine()
    print("释放数据库链接资源")
    await close_http_client()
    print("停止服务器")
app = FastAPI(description="电商小二智能客服应用",lifespan=lifespan)
app.include_router(router)