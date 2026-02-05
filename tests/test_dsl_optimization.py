#!/usr/bin/env python3
"""
测试1+3优化策略的效果
使用pytest框架进行单元测试
"""

import pytest
import sys
import os
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from py_script.utils.concsistency_checker import ProposalConsistencyChecker
from py_script.utils.function_mapper import get_mapping_cache, LOCAL_FUNCTION_MAPPINGS

# 获取全局映射缓存实例
mapping_cache = get_mapping_cache()


class TestFunctionMapping:
    """测试函数映射的各个层级"""

    def test_local_mapping_hits(self):
        """测试本地映射命中"""
        test_cases = [
            ("transfer", "Transfer(token, to, amount)"),
            ("transferFrom", "Transfer(token, to, amount)"),
            ("mint", "Mint(token, to, amount)"),
            ("burn", "Burn(token, from, amount)"),
            ("execute", "Execute(targets, values, calldatas, descriptionHash)"),
            ("propose", "Propose(targets, values, signatures, calldatas, description)"),
            ("vote", "Vote(proposalId, support)"),
            ("delegate", "Delegate(delegatee)"),
        ]
        
        for func_name, expected_primitive in test_cases:
            result = mapping_cache.map_function_to_primitive(func_name)
            assert result == expected_primitive, f"函数 {func_name} 映射错误: 期望 {expected_primitive}, 实际 {result}"

    def test_prefix_matching(self):
        """测试前缀模式匹配"""
        test_cases = [
            ("transferCustom", "Transfer(token, to, amount)"),
            ("mintTokens", "Mint(token, to, amount)"),
            ("burnAll", "Burn(token, from, amount)"),
            ("executeCall", "Execute(targets, values, calldatas, descriptionHash)"),
        ]
        
        for func_name, expected_primitive in test_cases:
            result = mapping_cache.map_function_to_primitive(func_name)
            assert result == expected_primitive, f"前缀匹配失败: {func_name} -> {result}, 期望 {expected_primitive}"

    def test_unknown_function_fallback(self):
        """测试未知函数的默认fallback"""
        unknown_functions = [
            "unknownFunction123",
            "anotherUnknown",
            "customFunction",
            "randomFunc"
        ]
        
        expected_default = "Call(target, function_sig, args)"
        
        for func_name in unknown_functions:
            result = mapping_cache.map_function_to_primitive(func_name)
            assert result == expected_default, f"未知函数 {func_name} 应该使用默认fallback"

    def test_cache_functionality(self):
        """测试缓存机制"""
        # 清空缓存
        mapping_cache.cached_mappings.clear()
        
        func_name = "testCacheFunction"
        
        # 第一次调用
        result1 = mapping_cache.map_function_to_primitive(func_name)
        assert func_name in mapping_cache.cached_mappings
        
        # 第二次调用应该从缓存获取
        result2 = mapping_cache.map_function_to_primitive(func_name)
        assert result1 == result2
        assert func_name in mapping_cache.cached_mappings

    def test_local_mappings_loaded(self):
        """测试本地映射表是否正确加载"""
        # 通过映射缓存获取本地映射
        cache = get_mapping_cache()
        assert len(cache.local_mappings) > 0, "本地映射表应该包含函数映射"
        
        # 测试一些关键函数存在
        key_functions = ["transfer", "mint", "burn", "execute"]
        for func in key_functions:
            assert func in cache.local_mappings, f"关键函数 {func} 应该存在于本地映射表中"


class TestTraceProcessing:
    """测试trace数据处理功能"""

    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.checker = ProposalConsistencyChecker(api_key="dummy-key-for-testing")

    def test_extract_functions_from_trace(self):
        """测试从trace数据中提取函数"""
        sample_trace = {
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
                }
            ]
        }
        
        functions = self.checker.extract_functions_from_trace(sample_trace)
        expected_functions = ["transfer", "mint"]
        
        assert functions == expected_functions, f"提取的函数列表不正确: {functions}"

    def test_extract_functions_from_string_trace(self):
        """测试从字符串格式trace中提取函数"""
        import json
        
        sample_trace = {
            "data": [
                {"trace": {"decoded": {"function": "delegate", "args": ["0x789..."]}}}
            ]
        }
        
        trace_string = json.dumps(sample_trace)
        functions = self.checker.extract_functions_from_trace(trace_string)
        
        assert functions == ["delegate"], f"从字符串trace提取函数失败: {functions}"

    def test_convert_trace_to_dsl_local(self):
        """测试本地trace转DSL功能"""
        sample_trace = {
            "data": [
                {"trace": {"decoded": {"function": "transfer", "args": ["0x123...", "1000000"]}}},
                {"trace": {"decoded": {"function": "mint", "args": ["0x456...", "500000"]}}},
                {"trace": {"decoded": {"function": "delegate", "args": ["0x789..."]}}}
            ]
        }
        
        dsl_actions = self.checker.convert_trace_to_dsl_local(sample_trace)
        
        # 验证DSL数量正确
        assert len(dsl_actions) == 3, f"应该有3个DSL动作: {len(dsl_actions)}"
        
        # 验证每个DSL包含正确的函数名和参数
        assert "Transfer(" in dsl_actions[0], f"第一个应该是Transfer动作: {dsl_actions[0]}"
        assert "function:transfer" in dsl_actions[0], f"应该包含原函数名: {dsl_actions[0]}"
        assert "args:" in dsl_actions[0], f"应该包含参数信息: {dsl_actions[0]}"
        
        assert "Mint(" in dsl_actions[1], f"第二个应该是Mint动作: {dsl_actions[1]}" 
        assert "function:mint" in dsl_actions[1], f"应该包含原函数名: {dsl_actions[1]}"
        assert "args:" in dsl_actions[1], f"应该包含参数信息: {dsl_actions[1]}"
        
        assert "Delegate(" in dsl_actions[2], f"第三个应该是Delegate动作: {dsl_actions[2]}"
        assert "function:delegate" in dsl_actions[2], f"应该包含原函数名: {dsl_actions[2]}"
        assert "args:" in dsl_actions[2], f"应该包含参数信息: {dsl_actions[2]}"

    def test_empty_trace_handling(self):
        """测试空trace数据的处理"""
        empty_traces = [
            {},
            {"data": []},
            [],
            ""
        ]
        
        for empty_trace in empty_traces:
            functions = self.checker.extract_functions_from_trace(empty_trace)
            assert functions == [], f"空trace应该返回空列表: {functions}"
            
            dsl_actions = self.checker.convert_trace_to_dsl_local(empty_trace)
            assert dsl_actions == [], f"空trace的DSL转换应该返回空列表: {dsl_actions}"


class TestOptimizationMetrics:
    """测试优化效果指标"""

    def test_cache_statistics(self):
        """测试缓存统计"""
        # 清空状态
        mapping_cache.cached_mappings.clear()
        mapping_cache.clear_unknown_functions()
        
        # 测试一些函数调用
        test_functions = [
            "transfer", "mint", "burn",  # 本地映射
            "transferCustom", "mintTokens",  # 前缀匹配
            "unknownFunc1", "unknownFunc2"  # 未知函数
        ]
        
        for func in test_functions:
            mapping_cache.map_function_to_primitive(func)
        
        # 验证统计数据
        assert len(mapping_cache.cached_mappings) == len(test_functions)
        assert len(mapping_cache.get_unknown_functions()) == 2  # 两个未知函数

    def test_mapping_distribution(self):
        """测试映射分布统计"""
        test_functions = [
            "transfer", "transferFrom", "mint", "burn", "execute",  # 本地映射 (5个)
            "transferCustom", "mintTokens", "burnAll",  # 前缀匹配 (3个)
            "unknownFunc1", "randomFunction"  # 未知函数 (2个)
        ]
        
        results = {}
        default_primitive = "Call(target, function_sig, args)"
        
        for func in test_functions:
            primitive = mapping_cache.map_function_to_primitive(func)
            results[func] = primitive
        
        # 统计各类型数量
        local_hits = sum(1 for func in test_functions[:5] 
                        if results[func] != default_primitive)
        prefix_hits = sum(1 for func in test_functions[5:8] 
                         if results[func] != default_primitive)
        unknown_count = sum(1 for func in test_functions[8:] 
                           if results[func] == default_primitive)
        
        assert local_hits >= 4, f"本地映射命中率过低: {local_hits}/5"
        assert prefix_hits >= 2, f"前缀匹配命中率过低: {prefix_hits}/3"
        assert unknown_count == 2, f"未知函数处理错误: {unknown_count}/2"


class TestPerformance:
    """性能相关测试"""

    def test_mapping_speed(self):
        """测试映射查找速度"""
        import time
        
        # 测试大量函数映射的速度
        test_functions = ["transfer"] * 1000
        
        start_time = time.time()
        for func in test_functions:
            mapping_cache.map_function_to_primitive(func)
        end_time = time.time()
        
        duration = end_time - start_time
        # 1000次映射应该在1秒内完成
        assert duration < 1.0, f"映射速度过慢: {duration:.3f}秒"

    def test_memory_efficiency(self):
        """测试内存使用效率"""
        # 清空缓存
        mapping_cache.cached_mappings.clear()
        
        # 映射大量不同的函数
        unique_functions = [f"func_{i}" for i in range(100)]
        
        for func in unique_functions:
            mapping_cache.map_function_to_primitive(func)
        
        # 缓存大小应该等于唯一函数数量
        assert len(mapping_cache.cached_mappings) == len(unique_functions)


@pytest.fixture(scope="session")
def setup_test_environment():
    """会话级别的测试环境设置"""
    # 确保测试环境干净
    if hasattr(mapping_cache, 'cached_mappings'):
        mapping_cache.cached_mappings.clear()
    if hasattr(mapping_cache, 'unknown_functions'):
        mapping_cache.clear_unknown_functions()
    
    yield
    
    # 测试结束后清理
    if hasattr(mapping_cache, 'cached_mappings'):
        mapping_cache.cached_mappings.clear()


def test_integration_workflow(setup_test_environment):
    """集成测试：完整的工作流程"""
    checker = ProposalConsistencyChecker(api_key="dummy-key-for-testing")
    
    # 模拟完整的trace处理流程
    sample_trace = {
        "data": [
            {"trace": {"decoded": {"function": "transfer", "args": ["0x123", "1000"]}}},
            {"trace": {"decoded": {"function": "propose", "args": ["targets", "values"]}}},
            {"trace": {"decoded": {"function": "vote", "args": ["1", "true"]}}}
        ]
    }
    
    # 提取函数
    functions = checker.extract_functions_from_trace(sample_trace)
    assert len(functions) == 3
    
    # 转换为DSL
    dsl_actions = checker.convert_trace_to_dsl_local(sample_trace)
    assert len(dsl_actions) == 3
    
    # 验证DSL类型正确（新格式包含函数名和参数）
    assert "Transfer(" in dsl_actions[0], f"第一个应该是Transfer: {dsl_actions[0]}"
    assert "function:transfer" in dsl_actions[0], f"应该包含原函数名: {dsl_actions[0]}"
    assert "args:" in dsl_actions[0], f"应该包含参数: {dsl_actions[0]}"
    
    assert "Propose(" in dsl_actions[1], f"第二个应该是Propose: {dsl_actions[1]}"
    assert "function:propose" in dsl_actions[1], f"应该包含原函数名: {dsl_actions[1]}"
    assert "args:" in dsl_actions[1], f"应该包含参数: {dsl_actions[1]}"
    
    assert "Vote(" in dsl_actions[2], f"第三个应该是Vote: {dsl_actions[2]}"
    assert "function:vote" in dsl_actions[2], f"应该包含原函数名: {dsl_actions[2]}"
    assert "args:" in dsl_actions[2], f"应该包含参数: {dsl_actions[2]}"


if __name__ == "__main__":
    # 如果直接运行此文件，执行所有测试
    pytest.main([__file__, "-v"])