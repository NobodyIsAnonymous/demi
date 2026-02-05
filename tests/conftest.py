"""
pytest配置文件
定义测试fixtures和全局配置
"""

import pytest
import sys
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_path():
    """返回项目根目录路径"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="function")
def clean_cache():
    """每个测试函数执行前清理缓存"""
    from py_script.utils.function_mapper import get_mapping_cache
    cache = get_mapping_cache()
    
    # 测试前清理
    cache.clear_cache()
    
    yield
    
    # 测试后清理
    cache.clear_cache()


@pytest.fixture(scope="function")
def sample_checker():
    """提供一个测试用的checker实例"""
    from py_script.utils.concsistency_checker import ProposalConsistencyChecker
    return ProposalConsistencyChecker(api_key="dummy-key-for-testing")


@pytest.fixture(scope="function")
def sample_trace_data():
    """提供示例trace数据"""
    return {
        "data": [
            {
                "trace": {
                    "decoded": {
                        "function": "transfer",
                        "args": ["0x123...", "1000000"]
                    }
                }
            },
            {
                "trace": {
                    "decoded": {
                        "function": "mint",
                        "args": ["0x456...", "500000"]
                    }
                }
            },
            {
                "trace": {
                    "decoded": {
                        "function": "delegate",
                        "args": ["0x789..."]
                    }
                }
            }
        ]
    }


def pytest_configure(config):
    """pytest启动时的配置"""
    # 添加自定义标记
    config.addinivalue_line("markers", "unit: 单元测试标记")
    config.addinivalue_line("markers", "integration: 集成测试标记")
    config.addinivalue_line("markers", "performance: 性能测试标记")


def pytest_collection_modifyitems(config, items):
    """修改测试项收集"""
    # 为没有标记的测试自动添加unit标记
    for item in items:
        if not any(mark.name in ["unit", "integration", "performance"] for mark in item.iter_markers()):
            item.add_marker(pytest.mark.unit)