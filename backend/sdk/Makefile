# ABD SDK Makefile
# 在 abd_sdk 目录下运行，所有源码都在 src 目录中

.PHONY: help clean build install test lint format docs clean-all

# 默认目标
help:
	@echo "ABD SDK 构建系统"
	@echo "=================="
	@echo ""
	@echo "可用目标:"
	@echo "  help      - 显示此帮助信息"
	@echo "  clean     - 清理构建文件"
	@echo "  build     - 构建SDK (源码包 + wheel包)"
	@echo "  install   - 安装SDK到当前环境"
	@echo "  test      - 运行测试"
	@echo "  lint      - 代码质量检查"
	@echo "  format    - 代码格式化"
	@echo "  docs      - 生成文档"
	@echo "  clean-all - 完全清理 (包括安装的包)"
	@echo "  dev       - 开发模式安装"
	@echo "  dist      - 仅构建分发包"
	@echo "  wheel     - 仅构建wheel包"
	@echo "  sdist     - 仅构建源码包"
	@echo ""
	@echo "使用示例:"
	@echo "  make build install    # 构建并安装"
	@echo "  make clean build      # 清理后构建"
	@echo "  make test             # 运行测试"

# 检查环境
check-env:
	@echo "检查构建环境..."
	@python -c "import sys; print(f'Python版本: {sys.version}')"
	@python -c "import setuptools; print('setuptools可用')"
	@python -c "import wheel; print('wheel可用')"
	@echo "环境检查完成"

# 清理构建文件
clean:
	@echo "🧹 清理构建文件..."
	@rm -rf build/
	@rm -rf dist/
	@rm -rf *.egg-info/
	@echo "✅ 构建文件清理完成"

# 构建SDK
build: check-env clean
	@echo "🔨 构建ABD SDK..."
	@python setup.py sdist bdist_wheel
	@echo "✅ SDK构建完成"
	@echo "生成的文件:"
	@ls -la dist/

# 仅构建分发包
dist: check-env clean
	@echo "📦 构建分发包..."
	@python setup.py sdist bdist_wheel
	@echo "✅ 分发包构建完成"

# 仅构建源码包
sdist: check-env clean
	@echo "📦 构建源码包..."
	@python setup.py sdist
	@echo "✅ 源码包构建完成"

# 仅构建wheel包
wheel: check-env clean
	@echo "📦 构建wheel包..."
	@python setup.py bdist_wheel
	@echo "✅ wheel包构建完成"

# 安装SDK
install: build
	@echo "📥 安装ABD SDK..."
	@pip install dist/*.whl
	@echo "✅ SDK安装完成"

# 开发模式安装
dev: check-env
	@echo "🔧 开发模式安装..."
	@pip install -e .
	@echo "✅ 开发模式安装完成"

# 强制重新安装
reinstall: clean-all install
	@echo "✅ SDK重新安装完成"

# 运行测试
test: check-env
	@echo "🧪 运行测试..."
	@python -m pytest src/tests/ -v
	@echo "✅ 测试完成"

# 代码质量检查
lint: check-env
	@echo "🔍 代码质量检查..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 src/ --max-line-length=120 --ignore=E501,W503; \
	else \
		echo "⚠️  flake8未安装，跳过代码检查"; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		mypy src/ --ignore-missing-imports; \
	else \
		echo "⚠️  mypy未安装，跳过类型检查"; \
	fi
	@echo "✅ 代码质量检查完成"

# 代码格式化
format: check-env
	@echo "🎨 代码格式化..."
	@if command -v black >/dev/null 2>&1; then \
		black src/ --line-length=120; \
	else \
		echo "⚠️  black未安装，跳过代码格式化"; \
	fi
	@if command -v isort >/dev/null 2>&1; then \
		isort src/ --profile=black; \
	else \
		echo "⚠️  isort未安装，跳过导入排序"; \
	fi
	@echo "✅ 代码格式化完成"

# 生成文档
docs: check-env
	@echo "📚 生成文档..."
	@if command -v sphinx-build >/dev/null 2>&1; then \
		mkdir -p docs/build; \
		sphinx-build -b html docs/source docs/build/html; \
		echo "✅ 文档生成完成"; \
	else \
		echo "⚠️  sphinx-build未安装，跳过文档生成"; \
	fi

# 完全清理
clean-all: clean
	@echo "🧹 完全清理..."
	@pip uninstall -y abd-sdk || true
	@echo "✅ 完全清理完成"

# 显示包信息
info: check-env
	@echo "📋 包信息:"
	@python setup.py --name --version --description
	@echo ""
	@echo "依赖信息:"
	@python setup.py --requires

# 验证源码结构
verify: check-env
	@echo "🔍 验证源码结构..."
	@python -c "
import os
required_files = [
    'src/__init__.py',
    'src/client.py',
    'src/config.py',
    'src/exceptions.py',
    'src/http_client.py',
    'src/logger.py',
    'src/api/__init__.py',
    'src/api/base.py'
]
missing = [f for f in required_files if not os.path.exists(f)]
if missing:
    print('❌ 缺失文件:')
    for f in missing:
        print(f'  - {f}')
    exit(1)
else:
    print('✅ 源码结构验证通过')
"
	@echo "✅ 源码结构验证完成"

# 快速构建和安装
all: verify build install
	@echo "🎉 完整构建流程完成！"

# 默认目标
.DEFAULT_GOAL := help
