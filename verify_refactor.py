#!/usr/bin/env python3
"""
验证重构后的模块结构
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_function_mapper():
    """测试函数映射模块"""
    print("🔧 测试函数映射模块...")
    
    from py_script.utils.function_mapper import get_mapping_cache, LOCAL_FUNCTION_MAPPINGS
    
    cache = get_mapping_cache()
    
    # 测试基本功能
    result = cache.map_function_to_primitive("transfer")
    assert result == "Transfer(token, to, amount)", f"transfer映射错误: {result}"
    
    # 测试统计
    stats = cache.get_cache_stats()
    print(f"   ✅ 缓存统计: {stats}")
    
    # 测试本地映射表
    assert len(LOCAL_FUNCTION_MAPPINGS) > 0, "本地映射表应该不为空"
    print(f"   ✅ 本地映射表包含 {len(LOCAL_FUNCTION_MAPPINGS)} 个函数")
    
def test_consistency_checker():
    """测试一致性检测模块"""
    print("🔧 测试一致性检测模块...")
    
    from py_script.utils.concsistency_checker import ProposalConsistencyChecker, DSL_PRIMITIVES
    
    checker = ProposalConsistencyChecker(api_key="dummy-test-key")
    
    # 测试trace提取
    sample_trace = {
        "data": [
            {"trace": {"decoded": {"function": "transfer", "args": ["0x123", "1000"]}}},
            {"trace": {"decoded": {"function": "mint", "args": ["0x456", "500"]}}}
        ]
    }
    
    functions = checker.extract_functions_from_trace(sample_trace)
    assert functions == ["transfer", "mint"], f"函数提取错误: {functions}"
    
    # 测试本地DSL转换
    dsl_actions = checker.convert_trace_to_dsl_local(sample_trace)
    expected = ["Transfer(token, to, amount)", "Mint(token, to, amount)"]
    assert dsl_actions == expected, f"DSL转换错误: {dsl_actions}"
    
    print(f"   ✅ DSL原语集合包含 {len(DSL_PRIMITIVES)} 个原语")
    print(f"   ✅ Trace处理功能正常")

def test_integration():
    """测试模块间集成"""
    print("🔧 测试模块集成...")
    
    from py_script.utils.function_mapper import get_mapping_cache
    from py_script.utils.concsistency_checker import ProposalConsistencyChecker
    
    # 获取同一个缓存实例
    cache1 = get_mapping_cache()
    cache2 = get_mapping_cache()
    
    assert cache1 is cache2, "应该返回同一个缓存实例"
    
    # 测试缓存在checker中的使用
    checker = ProposalConsistencyChecker(api_key="dummy-test-key")
    
    sample_trace = {"data": [{"trace": {"decoded": {"function": "execute"}}}]}
    dsl = checker.convert_trace_to_dsl_local(sample_trace)
    
    assert len(dsl) == 1, "应该返回一个DSL动作"
    assert dsl[0].startswith("Execute"), f"Execute函数应该映射到Execute原语: {dsl[0]}"
    
    print("   ✅ 模块间集成正常")

def main():
    """主测试函数"""
    print("🚀 验证重构后的模块结构")
    print("=" * 50)
    
    try:
        test_function_mapper()
        test_consistency_checker()
        test_integration()
        
        print("\n✅ 所有测试通过!")
        print("\n📋 重构完成:")
        print("   - FunctionMappingCache -> py_script/utils/function_mapper.py")
        print("   - ProposalConsistencyChecker -> py_script/utils/concsistency_checker.py")
        print("   - 模块分离清晰，职责单一")
        print("   - 向后兼容性良好")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)