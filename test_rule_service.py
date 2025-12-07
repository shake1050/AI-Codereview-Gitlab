# -*- coding: utf-8 -*-
"""规则服务测试脚本"""
import os
from pathlib import Path

# 设置项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
os.environ['PROJECT_ROOT'] = str(PROJECT_ROOT)

from biz.service.rule_service import RuleService
from biz.utils.code_reviewer import CodeReviewer

def test_rule_import():
    """测试从YAML导入规则"""
    print("\n=== 测试1: 从YAML导入规则 ===")
    success = RuleService.import_from_yaml('code_review_prompt', 'test_user')
    print(f"导入结果: {'成功' if success else '失败'}")
    return success

def test_rule_query():
    """测试规则查询"""
    print("\n=== 测试2: 查询规则 ===")
    try:
        rule = RuleService.get_rule('code_review_prompt')
        print(f"规则键名: {rule['rule_key']}")
        print(f"System Prompt 长度: {len(rule['system_prompt'])} 字符")
        print(f"User Prompt 长度: {len(rule['user_prompt'])} 字符")
        print(f"最后修改人: {rule.get('updated_by', 'N/A')}")
        return True
    except Exception as e:
        print(f"查询失败: {e}")
        return False

def test_rule_update():
    """测试规则更新"""
    print("\n=== 测试3: 更新规则 ===")
    try:
        # 获取当前规则
        rule = RuleService.get_rule('code_review_prompt')
        
        # 修改规则（添加测试标记）
        new_system_prompt = rule['system_prompt'] + "\n\n# 测试修改标记"
        new_user_prompt = rule['user_prompt']
        
        success = RuleService.update_rule(
            'code_review_prompt',
            new_system_prompt,
            new_user_prompt,
            'test_user',
            '测试规则更新功能'
        )
        
        print(f"更新结果: {'成功' if success else '失败'}")
        
        if success:
            # 验证更新
            updated_rule = RuleService.get_rule('code_review_prompt')
            if '测试修改标记' in updated_rule['system_prompt']:
                print("✓ 规则更新已生效")
                return True
            else:
                print("✗ 规则更新未生效")
                return False
        return success
    except Exception as e:
        print(f"更新失败: {e}")
        return False

def test_rule_history():
    """测试历史记录查询"""
    print("\n=== 测试4: 查询历史记录 ===")
    try:
        history_df = RuleService.get_rule_history('code_review_prompt', limit=10)
        print(f"历史记录数量: {len(history_df)}")
        
        if not history_df.empty:
            print("\n最近的历史记录:")
            for idx, row in history_df.head(3).iterrows():
                print(f"  - {row['change_type']} by {row['changed_by']} at {row['changed_at']}")
        
        return True
    except Exception as e:
        print(f"查询历史失败: {e}")
        return False

def test_code_reviewer_hot_reload():
    """测试规则热更新（直接测试规则加载）"""
    print("\n=== 测试5: 规则热更新 ===")
    try:
        # 第一次加载规则
        print("第一次加载规则...")
        rule1 = RuleService.get_rule('code_review_prompt')
        system_prompt1 = rule1['system_prompt']
        
        # 修改规则
        print("修改规则...")
        new_system_prompt = system_prompt1 + "\n\n# 热更新测试标记"
        RuleService.update_rule(
            'code_review_prompt',
            new_system_prompt,
            rule1['user_prompt'],
            'test_user',
            '测试热更新'
        )
        
        # 第二次加载规则
        print("第二次加载规则...")
        rule2 = RuleService.get_rule('code_review_prompt')
        system_prompt2 = rule2['system_prompt']
        
        # 验证规则已更新
        if '热更新测试标记' in system_prompt2 and '热更新测试标记' not in system_prompt1:
            print("✓ 热更新功能正常 - 规则立即生效")
            return True
        else:
            print("✗ 热更新功能异常")
            return False
            
    except Exception as e:
        print(f"热更新测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_all_rules():
    """测试获取所有规则"""
    print("\n=== 测试6: 获取所有规则列表 ===")
    try:
        rules_df = RuleService.get_all_rules()
        print(f"规则总数: {len(rules_df)}")
        
        if not rules_df.empty:
            print("\n规则列表:")
            for idx, row in rules_df.iterrows():
                print(f"  - {row['rule_key']} (活跃: {row['is_active']})")
        
        return True
    except Exception as e:
        print(f"获取规则列表失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("=" * 60)
    print("AI Review 规则管理系统 - 集成测试")
    print("=" * 60)
    
    tests = [
        ("YAML导入", test_rule_import),
        ("规则查询", test_rule_query),
        ("规则更新", test_rule_update),
        ("历史记录", test_rule_history),
        ("热更新", test_code_reviewer_hot_reload),
        ("规则列表", test_all_rules),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n测试 {name} 发生异常: {e}")
            results.append((name, False))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:20s} {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")

if __name__ == "__main__":
    main()
