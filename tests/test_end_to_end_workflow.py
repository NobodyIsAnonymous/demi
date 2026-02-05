#!/usr/bin/env python3
"""
端到端测试：完整的提案一致性检测工作流程
基于 sim_check.ipynb 中的实际执行结果创建测试断言
"""

import pytest
import sys
import os
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from py_script.utils.concsistency_checker import ProposalConsistencyChecker


class TestEndToEndWorkflow:
    """端到端工作流程测试"""
    
    @pytest.fixture(scope="class")
    def test_data_paths(self):
        """测试数据路径配置"""
        return {
            'params_dir': "data/ES_proposal_data/params",
            'traces_dir': "data/ES_proposal_data/traces_decoded_cleaned"
        }
    
    @pytest.fixture(scope="class")
    def sample_contract_data(self, test_data_paths):
        """加载实际的测试合约数据"""
        params_dir = test_data_paths['params_dir']
        
        # 检查测试数据是否存在
        if not os.path.exists(params_dir):
            pytest.skip(f"Test data directory not found: {params_dir}")
        
        # 使用输出文件中的实际合约地址
        contract_address = "0x323a76393544d5ecca80cd6ef2a560c6a395b7e3"
        params_file = f"{contract_address}.json"
        params_path = os.path.join(params_dir, params_file)
        
        if not os.path.exists(params_path):
            pytest.skip(f"Test contract params file not found: {params_path}")
            
        with open(params_path, "r", encoding="utf-8") as f:
            params_dict = json.load(f)
        
        return {
            'contract_address': contract_address,
            'params_dict': params_dict
        }
    
    def get_trace_path(self, contract_address, proposal_id, traces_dir):
        """获取trace文件路径"""
        if isinstance(proposal_id, str) and (proposal_id.startswith("b'") or proposal_id.startswith("b\"")):
            try:
                pid_bytes = eval(proposal_id)
                pid_hex = pid_bytes.hex()[:8]
                trace_fname = f"Simulation-Hash{pid_hex}.json"
            except Exception:
                return None
        else:
            trace_fname = f"Simulation-{proposal_id}.json"
        return os.path.join(traces_dir, contract_address, trace_fname)
    
    def test_data_structure_validation(self, sample_contract_data, test_data_paths):
        """测试数据结构验证"""
        contract_address = sample_contract_data['contract_address']
        params_dict = sample_contract_data['params_dict']
        
        # 验证基本数据结构
        assert 'proposals' in params_dict, "参数字典应包含 'proposals' 键"
        proposals = params_dict.get('proposals', [])
        assert len(proposals) > 0, "应该有至少一个提案"
        
        # 验证提案结构
        for proposal in proposals:
            assert 'proposalId' in proposal, "每个提案应该有 proposalId"
            if 'parsed_parameters' in proposal:
                parsed_params = proposal['parsed_parameters']
                if 'description' in parsed_params:
                    description = parsed_params['description']
                    assert isinstance(description, str), "Description 应该是字符串"
                    assert len(description) > 0, "Description 不应为空"
    
    def test_trace_file_accessibility(self, sample_contract_data, test_data_paths):
        """测试trace文件可访问性"""
        contract_address = sample_contract_data['contract_address']
        params_dict = sample_contract_data['params_dict']
        traces_dir = test_data_paths['traces_dir']
        
        valid_traces_found = 0
        
        for proposal in params_dict.get('proposals', []):
            proposal_id = proposal.get('proposalId')
            description = proposal.get('parsed_parameters', {}).get('description')
            
            if not description:
                continue
                
            trace_path = self.get_trace_path(contract_address, proposal_id, traces_dir)
            
            if trace_path and os.path.exists(trace_path):
                # 验证trace文件格式
                with open(trace_path, "r", encoding="utf-8") as f:
                    trace_data = json.load(f)
                
                assert 'status' in trace_data, "Trace数据应包含status字段"
                assert 'data' in trace_data, "Trace数据应包含data字段"
                assert isinstance(trace_data['data'], list), "Trace data应为列表"
                
                valid_traces_found += 1
        
        assert valid_traces_found > 0, "应该至少找到一个有效的trace文件"
    
    @pytest.mark.integration
    def test_proposal_consistency_check_ep5(self, sample_contract_data, test_data_paths):
        """测试EP5提案的一致性检测（基于实际输出）"""
        contract_address = sample_contract_data['contract_address']
        traces_dir = test_data_paths['traces_dir']
        
        # EP5的实际测试数据（来自输出文件）
        ep5_proposal_id = "65967822514040846992464797266243157509206510058326665394616765053720727454968"
        ep5_description = """# Execute EP5
```
Set the temporary premium start price to $100,000 as described in [EP5](https://docs.ens.domains/v/governance/governance-proposals/ep5-executable-set-the-temporary-premium-start-price-to-usd100-000).
```"""
        
        # 查找对应的trace文件
        trace_path = self.get_trace_path(contract_address, ep5_proposal_id, traces_dir)
        
        if not trace_path or not os.path.exists(trace_path):
            pytest.skip(f"EP5 trace file not found: {trace_path}")
        
        with open(trace_path, "r", encoding="utf-8") as f:
            trace_data = json.load(f)
        
        # 运行一致性检测
        checker = ProposalConsistencyChecker(api_key="dummy-test-key")
        
        # 测试本地DSL转换（不需要实际API调用）
        trace_dsl = checker.convert_trace_to_dsl_local(trace_data)
        
        # 验证trace DSL结果（基于实际输出）
        assert len(trace_dsl) > 0, "Trace DSL不应为空"
        
        # 验证包含Execute动作（来自实际输出）
        execute_actions = [action for action in trace_dsl if action.startswith("Execute")]
        assert len(execute_actions) > 0, "应该包含Execute动作"
        
        # 验证包含SetParam动作（来自实际输出）
        setparam_actions = [action for action in trace_dsl if action.startswith("SetParam")]
        assert len(setparam_actions) > 0, "应该包含SetParam动作"
    
    @pytest.mark.integration
    def test_proposal_consistency_check_ep11(self, sample_contract_data, test_data_paths):
        """测试EP11提案的一致性检测（基于实际输出）"""
        contract_address = sample_contract_data['contract_address']
        traces_dir = test_data_paths['traces_dir']
        
        # EP11的实际测试数据
        ep11_proposal_id = "99882233577221676057992280816078245519848378270443751235073826886360950537295"
        ep11_description = """# Execute EP11
Executes [EP11](https://github.com/ensdomains/governance-docs/blob/1e381d6fd97c5d877b9c90d5941e471b6ae1bc8e/governance-proposals/ep11-executable-end-airdrop.md), "End the $ENS and EP2 airdrops"."""
        
        trace_path = self.get_trace_path(contract_address, ep11_proposal_id, traces_dir)
        
        if not trace_path or not os.path.exists(trace_path):
            pytest.skip(f"EP11 trace file not found: {trace_path}")
        
        with open(trace_path, "r", encoding="utf-8") as f:
            trace_data = json.load(f)
        
        # 运行一致性检测
        checker = ProposalConsistencyChecker(api_key="dummy-test-key")
        trace_dsl = checker.convert_trace_to_dsl_local(trace_data)
        
        # 验证trace DSL结果（基于实际输出）
        assert len(trace_dsl) > 0, "Trace DSL不应为空"
        
        # 验证包含多个Execute和Call动作
        execute_actions = [action for action in trace_dsl if action.startswith("Execute")]
        call_actions = [action for action in trace_dsl if action.startswith("Call")]
        
        assert len(execute_actions) >= 2, "应该包含至少2个Execute动作"
        assert len(call_actions) >= 2, "应该包含至少2个Call动作"
    
    def test_dsl_output_structure(self, sample_contract_data, test_data_paths):
        """测试DSL输出结构的正确性"""
        contract_address = sample_contract_data['contract_address']
        params_dict = sample_contract_data['params_dict']
        traces_dir = test_data_paths['traces_dir']
        
        checker = ProposalConsistencyChecker(api_key="dummy-test-key")
        
        for proposal in params_dict.get('proposals', [])[:2]:  # 只测试前2个
            proposal_id = proposal.get('proposalId')
            description = proposal.get('parsed_parameters', {}).get('description')
            
            if not description:
                continue
                
            trace_path = self.get_trace_path(contract_address, proposal_id, traces_dir)
            
            if not trace_path or not os.path.exists(trace_path):
                continue
            
            with open(trace_path, "r", encoding="utf-8") as f:
                trace_data = json.load(f)
            
            # 测试本地DSL转换
            trace_dsl = checker.convert_trace_to_dsl_local(trace_data)
            
            # 验证DSL格式
            assert isinstance(trace_dsl, list), "Trace DSL应该是列表"
            
            for action in trace_dsl:
                assert isinstance(action, str), "每个DSL动作应该是字符串"
                assert "(" in action and ")" in action, "DSL动作应该包含函数调用格式"
            
            break  # 测试一个有效case即可
    
    def test_trace_data_consistency(self, sample_contract_data, test_data_paths):
        """测试trace数据的一致性"""
        contract_address = sample_contract_data['contract_address']
        params_dict = sample_contract_data['params_dict']
        traces_dir = test_data_paths['traces_dir']
        
        success_count = 0
        
        for proposal in params_dict.get('proposals', [])[:3]:  # 测试前3个
            proposal_id = proposal.get('proposalId')
            description = proposal.get('parsed_parameters', {}).get('description')
            
            if not description:
                continue
                
            trace_path = self.get_trace_path(contract_address, proposal_id, traces_dir)
            
            if not trace_path or not os.path.exists(trace_path):
                continue
            
            with open(trace_path, "r", encoding="utf-8") as f:
                trace_data = json.load(f)
            
            # 验证trace数据结构
            assert trace_data.get('status') in ['Success', 'Failure'], "Status应该是Success或Failure"
            
            data_list = trace_data.get('data', [])
            for item in data_list:
                assert 'trace' in item, "每个data项应该包含trace字段"
                trace = item['trace']
                
                # 验证关键字段存在
                expected_keys = {'depth', 'success', 'caller', 'address', 'kind'}
                present_keys = set(trace.keys())
                
                # 至少应该有一些基本字段
                assert len(present_keys.intersection(expected_keys)) > 0, "Trace应该包含基本字段"
            
            success_count += 1
        
        assert success_count > 0, "应该至少成功验证一个trace文件"
    
    @pytest.mark.performance
    def test_processing_performance(self, sample_contract_data, test_data_paths):
        """测试处理性能"""
        import time
        
        contract_address = sample_contract_data['contract_address']
        params_dict = sample_contract_data['params_dict']
        traces_dir = test_data_paths['traces_dir']
        
        checker = ProposalConsistencyChecker(api_key="dummy-test-key")
        
        start_time = time.time()
        processed_count = 0
        
        for proposal in params_dict.get('proposals', [])[:5]:  # 测试前5个
            proposal_id = proposal.get('proposalId')
            description = proposal.get('parsed_parameters', {}).get('description')
            
            if not description:
                continue
                
            trace_path = self.get_trace_path(contract_address, proposal_id, traces_dir)
            
            if not trace_path or not os.path.exists(trace_path):
                continue
            
            with open(trace_path, "r", encoding="utf-8") as f:
                trace_data = json.load(f)
            
            # 执行本地DSL转换
            trace_dsl = checker.convert_trace_to_dsl_local(trace_data)
            processed_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        if processed_count > 0:
            avg_time_per_proposal = duration / processed_count
            assert avg_time_per_proposal < 1.0, f"平均每个提案处理时间应小于1秒，实际: {avg_time_per_proposal:.3f}秒"
    
    def test_error_handling(self, test_data_paths):
        """测试错误处理"""
        checker = ProposalConsistencyChecker(api_key="dummy-test-key")
        
        # 测试空trace数据
        empty_trace = {"status": "Success", "data": []}
        trace_dsl = checker.convert_trace_to_dsl_local(empty_trace)
        assert trace_dsl == [], "空trace应该返回空DSL列表"
        
        # 测试无效trace数据
        invalid_trace = {"invalid": "data"}
        trace_dsl = checker.convert_trace_to_dsl_local(invalid_trace)
        assert trace_dsl == [], "无效trace应该返回空DSL列表"
        
        # 测试异常trace格式
        malformed_trace = {"status": "Success", "data": [{"no_trace": "field"}]}
        trace_dsl = checker.convert_trace_to_dsl_local(malformed_trace)
        assert isinstance(trace_dsl, list), "格式错误的trace应该返回列表"


if __name__ == "__main__":
    # 如果直接运行此文件，执行所有测试
    pytest.main([__file__, "-v", "--tb=short"])