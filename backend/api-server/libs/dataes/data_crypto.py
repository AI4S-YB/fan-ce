#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project: oma
@File   : rsa.py
@IDE    : PyCharm
@Author: llq
@Date   : 2024/12/3 14:36
@version:  1.0
@Desc   : 
"""
import random
import subprocess
import requests
import threading
import secrets
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding


# 生成RSA密钥对
def createRsa():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    # PEM格式化
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_key = private_key.public_key()
    # PEM格式化
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # 将私钥保存到文件
    with open("private_key.pem", "wb") as private_file:
        private_file.write(private_pem)

    # 将公钥保存到文件
    with open("public_key.pem", "wb") as public_file:
        public_file.write(public_pem)


# 加密函数
def encrypt(message, public_key):
    ciphertext = public_key.encrypt(
        message.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext


# 解密函数
def decrypt(ciphertext, private_key):
    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext.decode()


def read_pem_public_key(pem_file_path):
    with open(pem_file_path, "rb") as pem_file:
        pem_data = pem_file.read()
        # 解析 PEM 格式的公钥
        public_key = serialization.load_pem_public_key(pem_data, backend=default_backend())
    return public_key


def read_pem_private_key(pem_file_path, password=None):
    with open(pem_file_path, "rb") as pem_file:
        pem_data = pem_file.read()
        private_key = serialization.load_pem_private_key(pem_data, password)
    return private_key


def sign_license(license_info, private_key):
    # 签名
    signature = private_key.sign(license_info.encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                                 hashes.SHA256())
    signature_str = base64.b64encode(signature).decode()
    return signature_str


def verify_license(license_info, signature_str, public_key):
    # 签名认证
    signature = base64.b64decode(signature_str.encode())
    try:
        public_key.verify(signature,
                          license_info.encode(),
                          padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                          hashes.SHA256())
        return True
    except Exception as e:
        return False


# 生成License
def generate_license(data, public_key):
    encrypted_data = encrypt(data, public_key)
    return encrypted_data.hex()


# 解密License
def decrypt_license(plaintext, private_key):
    ciphertext = bytes.fromhex(plaintext)
    data = decrypt(ciphertext, private_key)
    return data


def get_serial_number():
    sn = ''
    try:
        output = subprocess.check_output(['dmidecode', '-t', '1'], universal_newlines=True)
        lines = output.split('\n')
        for line in lines:
            if 'Serial Number:' in line:
                sn = line.split(':')[1].strip()
    except subprocess.CalledProcessError:
        print("Failed to retrieve mainboard serial number.")
    return sn
