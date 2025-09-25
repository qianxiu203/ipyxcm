#!/usr/bin/env python3
"""
GitHub Actions环境测试脚本
"""

import asyncio
import sys
from ip_optimizer import CloudflareIPOptimizer

async def test_github_actions():
    """测试GitHub Actions环境"""
    print("🧪 GitHub Actions环境测试")
    print("=" * 50)
    
    try:
        async with CloudflareIPOptimizer(
            target_country="US",
            max_ips=10,  # 限制IP数量以加快测试
            max_concurrent=4,  # 降低并发数
            target_count=2  # 只需要2个IP
        ) as optimizer:
            
            print(f"✅ 成功创建优化器")
            print(f"📡 使用的NIP域名: {optimizer.nip_domain}")
            
            # 测试获取IP列表
            print("\n1️⃣ 测试IP获取...")
            ips = await optimizer.get_cf_ips("official", "443")
            print(f"✅ 获取到 {len(ips)} 个IP")
            
            if ips:
                print("前3个IP:")
                for i, ip in enumerate(ips[:3], 1):
                    print(f"  {i}. {ip}")
                
                # 测试完整流程
                print("\n2️⃣ 测试完整优选流程...")
                results = await optimizer.get_country_ips_from_all_sources("443")
                
                if results:
                    print(f"✅ 找到 {len(results)} 个美国IP:")
                    for i, result in enumerate(results, 1):
                        print(f"  {i}. {result.to_display_format()}")
                    
                    # 保存结果
                    optimizer.save_results_to_file(results, "test_github_nodes.txt")
                    print("✅ 结果已保存到 test_github_nodes.txt")
                    
                else:
                    print("⚠️ 未找到任何美国IP，但脚本运行正常")
            else:
                print("⚠️ 未获取到任何IP，可能是网络问题")
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ GitHub Actions环境测试完成")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_github_actions())
        if success:
            print("🎉 测试成功！脚本可以在GitHub Actions中运行")
            sys.exit(0)
        else:
            print("❌ 测试失败")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        sys.exit(1)
