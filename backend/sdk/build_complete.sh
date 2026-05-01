#!/bin/bash

# ABD SDK 完整编译脚本 - 版本 3.0.1
# 适配当前目录结构: abd_sdk/abd_sdk/
# 支持 main 函数导入测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

print_step() {
    echo -e "\n${BLUE}============================================================"
    echo -e " $1"
    echo -e "============================================================${NC}"
}

# 检查当前目录
check_directory() {
    print_step "检查当前目录结构"
    
    if [[ ! -f "setup.py" ]]; then
        print_error "setup.py 不存在，请在 abd_sdk 目录下运行此脚本"
        exit 1
    fi
    
    if [[ ! -d "abd_sdk" ]]; then
        print_error "abd_sdk 包目录不存在"
        exit 1
    fi
    
    if [[ ! -f "abd_sdk/__init__.py" ]]; then
        print_error "abd_sdk/__init__.py 不存在"
        exit 1
    fi
    
    print_success "目录结构检查通过"
    print_info "当前目录: $(pwd)"
    print_info "包目录: abd_sdk/"
    print_info "版本: 3.0.1"
}

# 清理构建文件
clean_build() {
    print_step "清理构建文件"
    
    local cleaned=false
    
    # 清理构建目录
    if [[ -d "build" ]]; then
        rm -rf build/
        print_info "删除 build/ 目录"
        cleaned=true
    fi
    
    # 清理分发目录
    if [[ -d "dist" ]]; then
        rm -rf dist/
        print_info "删除 dist/ 目录"
        cleaned=true
    fi
    
    # 清理egg-info目录
    for egg_dir in *.egg-info; do
        if [[ -d "$egg_dir" ]]; then
            rm -rf "$egg_dir"
            print_info "删除 $egg_dir 目录"
            cleaned=true
        fi
    done
    
    # 清理__pycache__目录
    if [[ -d "__pycache__" ]]; then
        rm -rf __pycache__/
        print_info "删除 __pycache__/ 目录"
        cleaned=true
    fi
    
    if [[ -d "abd_sdk/__pycache__" ]]; then
        rm -rf abd_sdk/__pycache__/
        print_info "删除 abd_sdk/__pycache__/ 目录"
        cleaned=true
    fi
    
    if [[ "$cleaned" == true ]]; then
        print_success "构建文件清理完成"
    else
        print_info "没有找到需要清理的构建文件"
    fi
}

# 显示配置信息
show_config() {
    print_step "当前配置信息"
    
    print_info "setup.py 配置:"
    echo "  - 包名: abd_sdk"
    echo "  - 版本: 3.0.1"
    echo "  - 包发现: find_packages()"
    echo "  - 无 package_dir 配置"
    
    print_info "pyproject.toml 状态:"
    if grep -q "where = " pyproject.toml; then
        print_warning "发现 where 配置，已注释"
    else
        print_success "无冲突配置"
    fi
    
    print_info "包结构:"
    echo "  - abd_sdk/__init__.py"
    echo "  - abd_sdk/client.py"
    echo "  - abd_sdk/config.py"
    echo "  - abd_sdk/exceptions.py"
    echo "  - abd_sdk/http_client.py"
    echo "  - abd_sdk/logger.py"
    echo "  - abd_sdk/cli.py"
    echo "  - abd_sdk/api/"
    echo "  - abd_sdk/examples/"
    echo "  - abd_sdk/tests/"
    
    print_info "main函数导入配置:"
    if grep -q "from .cli import main" abd_sdk/__init__.py; then
        print_success "main函数已从cli模块导入"
        echo "  - 支持: from abd_sdk import main"
        echo "  - 支持: from abd_sdk.cli import main"
    else
        print_warning "main函数未从cli模块导入"
        echo "  - 仅支持: from abd_sdk.cli import main"
    fi
}

# 构建包
build_package() {
    print_step "构建包"
    
    print_info "执行构建命令..."
    print_info "命令: python setup.py sdist bdist_wheel"
    
    if python setup.py sdist bdist_wheel; then
        print_success "包构建成功"
        
        # 检查生成的文件
        if [[ -d "dist" ]]; then
            print_info "生成的文件:"
            ls -la dist/
        else
            print_error "dist 目录未生成"
            return 1
        fi
    else
        print_error "包构建失败"
        return 1
    fi
}

# 安装包
install_package() {
    print_step "安装包"
    
    # 查找最新的wheel文件
    local whl_file
    whl_file=$(ls -t dist/*.whl 2>/dev/null | head -1)
    
    if [[ -z "$whl_file" ]]; then
        print_error "未找到wheel文件"
        return 1
    fi
    
    print_info "安装wheel包: $whl_file"
    
    # 先卸载旧版本
    if pip show abd_sdk >/dev/null 2>&1; then
        print_info "卸载旧版本..."
        pip uninstall abd_sdk -y
    fi
    
    # 安装新版本
    if pip install "$whl_file"; then
        print_success "包安装成功"
    else
        print_error "包安装失败"
        return 1
    fi
}

# 验证安装
verify_installation() {
    print_step "验证安装"
    
    print_info "测试包导入..."
    
    if python -c "
import abd_sdk
print('✅ 包导入成功')
print(f'版本: {abd_sdk.__version__}')
print(f'作者: {abd_sdk.__author__}')
print(f'描述: {abd_sdk.__description__}')
"; then
        print_success "包安装验证通过"
    else
        print_error "包安装验证失败"
        return 1
    fi
    
    print_info "测试main函数导入..."
    
    # 检查是否支持从包根目录导入main
    if grep -q "from .cli import main" abd_sdk/__init__.py; then
        print_info "测试从包根目录导入main函数..."
        if python -c "
from abd_sdk import main
print('✅ 从包根目录导入main函数成功')
print(f'main函数类型: {type(main)}')
print(f'main函数名称: {main.__name__}')
"; then
            print_success "从包根目录导入main函数验证通过"
        else
            print_error "从包根目录导入main函数验证失败"
            return 1
        fi
    else
        print_info "测试从cli模块导入main函数..."
        if python -c "
from abd_sdk.cli import main
print('✅ 从cli模块导入main函数成功')
print(f'main函数类型: {type(main)}')
print(f'main函数名称: {main.__name__}')
"; then
            print_success "从cli模块导入main函数验证通过"
        else
            print_error "从cli模块导入main函数验证失败"
            return 1
        fi
    fi
    
    # 检查site-packages
    print_info "检查site-packages目录..."
    local site_packages
    site_packages=$(python -c "import site; print(site.getsitepackages()[0])" 2>/dev/null || python -c "import site; print(site.getusersitepackages())")
    
    if [[ -d "$site_packages/abd_sdk" ]]; then
        print_success "找到 abd_sdk 包目录: $site_packages/abd_sdk"
        ls -la "$site_packages/abd_sdk"
    else
        print_warning "未找到 abd_sdk 包目录"
    fi
    
    if ls "$site_packages"/abd_sdk-*.dist-info >/dev/null 2>&1; then
        print_success "找到 abd_sdk dist-info 目录"
        ls -la "$site_packages"/abd_sdk-*.dist-info
    else
        print_warning "未找到 abd_sdk dist-info 目录"
    fi
}

# 显示使用说明
show_usage() {
    print_step "使用说明"
    
    print_info "现在您可以使用以下方式导入和使用SDK:"
    echo ""
    echo "import abd_sdk"
    echo "client = abd_sdk.ABDClient()"
    echo "print(abd_sdk.__version__)  # 应该显示 3.0.1"
    echo ""
    
    print_info "main函数使用方式:"
    if grep -q "from .cli import main" abd_sdk/__init__.py; then
        echo "✅ 支持从包根目录导入:"
        echo "  from abd_sdk import main"
        echo "  main()  # 启动CLI"
        echo ""
        echo "✅ 也支持从cli模块导入:"
        echo "  from abd_sdk.cli import main"
        echo "  main()  # 启动CLI"
    else
        echo "✅ 支持从cli模块导入:"
        echo "  from abd_sdk.cli import main"
        echo "  main()  # 启动CLI"
    fi
    echo ""
    
    print_info "命令行工具:"
    echo "abd_sdk --help"
    echo ""
    
    print_info "如需卸载:"
    echo "pip uninstall abd_sdk"
}

# 主函数
main() {
    echo "ABD SDK 完整编译脚本 - 版本 3.0.1"
    echo "支持 main 函数导入测试"
    echo "============================================================"
    
    # 检查当前目录
    check_directory
    
    # 显示配置信息
    show_config
    
    # 清理构建文件
    clean_build
    
    # 构建包
    if ! build_package; then
        print_error "构建失败，脚本退出"
        exit 1
    fi
    
    # 安装包
    if ! install_package; then
        print_error "安装失败，脚本退出"
        exit 1
    fi
    
    # 验证安装
    if ! verify_installation; then
        print_error "验证失败，脚本退出"
        exit 1
    fi
    
    # 显示使用说明
    show_usage
    
    print_success "🎉 ABD SDK 编译和安装完成！"
}

# 执行主函数
main "$@"
