from fastapi.security import OAuth2PasswordBearer

# 创建 OAuth2PasswordBearer 依赖
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



