#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FAN-CE SDK Setup Configuration
用于编译打包ABD SDK
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return "FAN-CE SDK"

# 读取requirements文件
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        with open(requirements_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return []

setup(
    name="fance_sdk",
    version="3.0.1",
    author="kentnf, llq, kasper1995",
    author_email="abd@example.com",
    description="FAN-CE SDK",,
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/kentnf/fan-ce",
    project_urls={
        "Bug Reports": "https://github.com/kentnf/fan-ce/issues",
        "Source": "https://github.com/kentnf/fan-ce",
        "Documentation": "https://fan-ce.readthedocs.io/",
    },
    # 当前结构：包直接在abd_sdk目录下
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
            "sphinx>=4.0",
            "sphinx-rtd-theme>=0.5",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "pytest-mock>=3.0",
            "responses>=0.12",
        ],
        "docs": [
            "sphinx>=4.0",
            "sphinx-rtd-theme>=0.5",
            "sphinx-autodoc-typehints>=1.12",
        ],
    },
    entry_points={
        "console_scripts": [
            "fance_sdk=fance_sdk.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "abd_sdk": [
            "*.txt",
            "*.md",
            "*.yaml",
            "*.yml",
            "*.json",
        ],
    },
    zip_safe=False,
    keywords=[
        "bioinformatics",
        "genomics",
        "api",
        "sdk",
        "science",
        "research",
        "data-analysis",
    ],
)
