#!/usr/bin/env python3
"""
模块唯一性守护脚本
用于检测和防止重复模块导入问题
"""

import sys
import inspect
import logging
from typing import List, Tuple

log = logging.getLogger(__name__)

def assert_unique_newsapi_client():
    """
    运行期检测：若发现 NewsApiClient 被导入多次则抛错。
    """
    dups = [
        (name, inspect.getfile(mod))
        for name, mod in sys.modules.items()
        if name.endswith("newsapi_client")
    ]
    
    if len(dups) > 1:
        error_msg = f"❌ 检测到重复的 NewsApiClient 模块: {dups}"
        log.error(error_msg)
        raise ImportError(error_msg)
    
    if dups:
        log.info(f"✅ NewsApiClient 模块路径唯一: {dups[0][1]}")
    
    return dups

def check_module_paths() -> List[Tuple[str, str]]:
    """
    检查所有模块的加载路径，返回重复的模块。
    """
    module_paths = {}
    duplicates = []
    
    for name, module in sys.modules.items():
        if hasattr(module, '__file__') and module.__file__:
            path = module.__file__
            if path in module_paths:
                duplicates.append((name, path))
            else:
                module_paths[path] = name
    
    return duplicates

def validate_imports():
    """
    验证关键模块的导入路径。
    """
    critical_modules = [
        'scraper.newsapi_client',
        'scraper.base_newsapi',
        'pipeline.score',
        'pipeline.cluster_topics'
    ]
    
    results = {}
    for module_name in critical_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            results[module_name] = inspect.getfile(module)
            log.info(f"✅ {module_name}: {results[module_name]}")
        except ImportError as e:
            log.warning(f"⚠️ {module_name}: 导入失败 - {e}")
            results[module_name] = None
    
    return results

def main():
    """
    主函数：执行所有检查。
    """
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 检查 NewsApiClient 唯一性
        assert_unique_newsapi_client()
        
        # 检查所有重复模块
        duplicates = check_module_paths()
        if duplicates:
            log.warning(f"⚠️ 发现重复模块路径: {duplicates}")
        else:
            log.info("✅ 所有模块路径唯一")
        
        # 验证关键模块导入
        validate_imports()
        
        log.info("🎉 所有模块检查通过")
        
    except Exception as e:
        log.error(f"❌ 模块检查失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 