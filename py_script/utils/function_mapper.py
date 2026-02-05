#!/usr/bin/env python3
"""
函数映射缓存模块
实现1+3优化策略的核心组件
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

# 全局变量：本地函数映射
LOCAL_FUNCTION_MAPPINGS = {}

def load_local_mappings() -> Dict[str, str]:
    """加载本地函数映射表"""
    global LOCAL_FUNCTION_MAPPINGS
    
    if LOCAL_FUNCTION_MAPPINGS:
        return LOCAL_FUNCTION_MAPPINGS
    
    # 获取function_to_primitive.json的路径
    current_dir = Path(__file__).parent.parent
    mapping_file = current_dir / "tools" / "function_to_primitive.json"
    
    try:
        if mapping_file.exists():
            with open(mapping_file, 'r', encoding='utf-8') as f:
                LOCAL_FUNCTION_MAPPINGS = json.load(f)
                print(f"✅ 成功加载 {len(LOCAL_FUNCTION_MAPPINGS)} 个本地函数映射")
        else:
            print(f"⚠️ 未找到本地映射文件: {mapping_file}")
            LOCAL_FUNCTION_MAPPINGS = {}
    except Exception as e:
        print(f"❌ 加载本地映射失败: {e}")
        LOCAL_FUNCTION_MAPPINGS = {}
    
    return LOCAL_FUNCTION_MAPPINGS


class FunctionMappingCache:
    """
    函数映射缓存类
    实现1+3优化策略：缓存 + 本地映射 + 前缀匹配 + 默认fallback
    """
    
    def __init__(self):
        """初始化映射缓存"""
        self.cached_mappings = {}  # 运行时缓存
        self.unknown_functions = []  # 记录未知函数
        
        # 前缀模式映射 - 智能前缀匹配
        self.prefix_patterns = {
            "transfer": "Transfer(token, to, amount)",
            "mint": "Mint(token, to, amount)", 
            "burn": "Burn(token, from, amount)",
            "execute": "Execute(targets, values, calldatas, descriptionHash)",
            "propose": "Propose(targets, values, signatures, calldatas, description)",
            "vote": "Vote(proposalId, support)",
            "cast": "Vote(proposalId, support)",
            "delegate": "Delegate(delegatee)",
            "queue": "Queue(proposalId)",
            "cancel": "Cancel(proposalId)",
            "approve": "Approve(token, spender, amount)",
            "swap": "Swap(tokenIn, tokenOut, amount)",
            "stake": "Stake(token, amount)",
            "unstake": "Unstake(token, amount)",
            "claim": "Claim(token, amount)",
            "deposit": "Deposit(token, amount)",
            "withdraw": "Withdraw(token, amount)",
        }
        
        # 加载本地映射
        self.local_mappings = load_local_mappings()
    
    def map_function_to_primitive(self, function_name: str) -> str:
        """
        将函数名映射为DSL原语
        使用1+3策略：缓存 -> 本地映射 -> 前缀匹配 -> 默认fallback
        """
        if not function_name:
            return "Call(target, function_sig, args)"
        
        # 第1层：缓存查找
        if function_name in self.cached_mappings:
            return self.cached_mappings[function_name]
        
        # 第2层：本地映射表查找
        if function_name in self.local_mappings:
            primitive = self.local_mappings[function_name]
            self.cached_mappings[function_name] = primitive
            return primitive
        
        # 第3层：前缀模式匹配
        for prefix, primitive in self.prefix_patterns.items():
            if function_name.lower().startswith(prefix.lower()):
                self.cached_mappings[function_name] = primitive
                return primitive
        
        # 第4层：默认fallback
        default_primitive = "Call(target, function_sig, args)"
        self.cached_mappings[function_name] = default_primitive
        
        # 记录未知函数
        if function_name not in self.unknown_functions:
            self.unknown_functions.append(function_name)
        
        return default_primitive
    
    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            "cached_functions": len(self.cached_mappings),
            "local_mappings": len(self.local_mappings),
            "prefix_patterns": len(self.prefix_patterns), 
            "unknown_functions": len(self.unknown_functions)
        }
    
    def get_unknown_functions(self) -> List[str]:
        """获取未知函数列表"""
        return self.unknown_functions.copy()
    
    def clear_cache(self):
        """清空缓存"""
        self.cached_mappings.clear()
    
    def clear_unknown_functions(self):
        """清空未知函数列表"""
        self.unknown_functions.clear()


# 全局缓存实例（单例模式）
_global_mapping_cache = None

def get_mapping_cache() -> FunctionMappingCache:
    """获取全局映射缓存实例（单例模式）"""
    global _global_mapping_cache
    
    if _global_mapping_cache is None:
        _global_mapping_cache = FunctionMappingCache()
    
    return _global_mapping_cache


if __name__ == "__main__":
    # 测试代码
    cache = get_mapping_cache()
    
    # 测试各层映射
    test_functions = [
        "transfer",      # 本地映射
        "transferCustom", # 前缀匹配
        "unknownFunc"    # 默认fallback
    ]
    
    print("=== 函数映射测试 ===")
    for func in test_functions:
        primitive = cache.map_function_to_primitive(func)
        print(f"{func:<15} -> {primitive}")
    
    print("\n=== 缓存统计 ===")
    stats = cache.get_cache_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\n=== 未知函数 ===")
    unknown = cache.get_unknown_functions()
    for func in unknown:
        print(f"- {func}")