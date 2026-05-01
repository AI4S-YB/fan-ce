"""
@File    :   security.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""

from typing import Any, Union
from datetime import datetime, timedelta
from jose import jwt
from jose.exceptions import JWTError,ExpiredSignatureError
from passlib.context import CryptContext

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


# 生成token
def create_access_token(subject: Union[int, str, Any], expires_delta: timedelta = None) -> str:
    """
    生成token
    :param subject: 字典
    :param expires_delta: 有效时间
    :return: 字符串
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "user_id": int(subject), 'iss': 'fan-ce-api', 'openid': 'openid', 'audience': 'openid','scope':{'openid':'openid'}}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 生成token
def create_token(subject: Union[dict, str, Any], expires_delta: timedelta = None) -> str:
    """
    生成token
    :param subject: 字典
    :param expires_delta: 有效时间
    :return: 字符串
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    if subject:
        to_encode = {**subject, **{"exp": expire}}
    else:
        to_encode = {"exp": expire}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# 验证明文密码 vs hash密码
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码 vs hash密码
    :param plain_password: 明文密码
    :param hashed_password: hash密码
    :return:
    """
    return pwd_context.verify(plain_password, hashed_password)


# 加密明文
def get_password_hash(password: str) -> str:
    """
    加密明文
    :param password: 明文密码
    :return:
    """
    return pwd_context.hash(password)


# 解密token
def check_jwt_token(token, secret_key=settings.SECRET_KEY, algorithms=ALGORITHM) -> dict:
    global payload
    try:
        payload = jwt.decode(token=token, key=secret_key,
                             algorithms=algorithms)
        print(payload)
    # 当然两个异常捕获也可以写在一起，不区分
    except ExpiredSignatureError:
        print("token过期")
    except JWTError:
        print("token验证失败")
    return payload


def check_token(token, secret_key=settings.SECRET_KEY, algorithms=ALGORITHM) -> dict:
    payload = {}
    try:
        payload = jwt.decode(token=token, key=secret_key,
                             algorithms=algorithms)
    # 当然两个异常捕获也可以写在一起，不区分
    except ExpiredSignatureError:
        print("token过期")
    except JWTError:
        print("token验证失败")
    return payload
