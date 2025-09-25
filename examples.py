#!/usr/bin/env python3
"""
使用示例脚本
演示如何使用 CloudflareIPOptimizer 类
"""

import asyncio
from ip_optimizer import CloudflareIPOptimizer

async def example_1_basic_usage():
    """示例1: 基本使用 - 获取中国地区IP"""
    print("=" * 60)
    print("示例1: 基本使用 - 获取中国地区IP")
    print("=" * 60)
    
    async with CloudflareIPOptimizer(target_country="CN") as optimizer:
        results = await optimizer.get_country_ips("official", "443")
        
        if results:
            print(f"\n找到 {len(results)} 个中国IP:")
            for i, result in enumerate(results[:5], 1):
                print(f"{i}. {result.to_display_format()}")
            
            # 保存结果
            optimizer.save_results_to_file(results, "cn_nodes.txt")
        else:
            print("未找到任何中国IP")

async def example_2_different_source():
    """示例2: 使用不同IP源"""
    print("\n" + "=" * 60)
    print("示例2: 使用CM整理的IP源")
    print("=" * 60)
    
    async with CloudflareIPOptimizer(
        target_country="US", 
        max_ips=100,  # 限制IP数量
        max_concurrent=16  # 降低并发数
    ) as optimizer:
        results = await optimizer.get_country_ips("cm", "443")
        
        if results:
            print(f"\n找到 {len(results)} 个美国IP:")
            for i, result in enumerate(results[:3], 1):
                print(f"{i}. {result.to_display_format()}")

async def example_3_different_port():
    """示例3: 使用不同端口"""
    print("\n" + "=" * 60)
    print("示例3: 使用2053端口")
    print("=" * 60)
    
    async with CloudflareIPOptimizer(
        target_country="JP",
        max_ips=50,
        max_concurrent=8
    ) as optimizer:
        results = await optimizer.get_country_ips("official", "2053")
        
        if results:
            print(f"\n找到 {len(results)} 个日本IP (端口2053):")
            for i, result in enumerate(results[:3], 1):
                print(f"{i}. {result.to_display_format()}")

async def example_4_multiple_countries():
    """示例4: 批量获取多个国家的IP"""
    print("\n" + "=" * 60)
    print("示例4: 批量获取多个国家的IP")
    print("=" * 60)
    
    countries = ["CN", "US", "JP", "HK"]
    
    for country in countries:
        print(f"\n正在获取 {country} 国家的IP...")
        
        async with CloudflareIPOptimizer(
            target_country=country,
            max_ips=20,  # 每个国家限制20个IP
            max_concurrent=8
        ) as optimizer:
            results = await optimizer.get_country_ips("official", "443")
            
            if results:
                print(f"✅ {country}: 找到 {len(results)} 个IP")
                # 保存到单独的文件
                optimizer.save_results_to_file(results, f"{country.lower()}_nodes.txt")
            else:
                print(f"❌ {country}: 未找到任何IP")

async def example_5_custom_settings():
    """示例5: 自定义设置"""
    print("\n" + "=" * 60)
    print("示例5: 自定义设置 - 高并发快速测试")
    print("=" * 60)
    
    async with CloudflareIPOptimizer(
        target_country="SG",  # 新加坡
        max_ips=200,          # 更多IP
        max_concurrent=64     # 更高并发
    ) as optimizer:
        results = await optimizer.get_country_ips("as13335", "8443")
        
        if results:
            print(f"\n找到 {len(results)} 个新加坡IP:")
            
            # 显示延迟分布
            latencies = [r.latency for r in results]
            print(f"延迟分布:")
            print(f"  最低: {min(latencies):.0f}ms")
            print(f"  最高: {max(latencies):.0f}ms") 
            print(f"  平均: {sum(latencies)/len(latencies):.0f}ms")
            
            # 显示前5个最优IP
            print(f"\n前5个最优IP:")
            for i, result in enumerate(results[:5], 1):
                print(f"  {i}. {result.to_display_format()}")

async def main():
    """运行所有示例"""
    print("🚀 Cloudflare IP优选脚本使用示例")
    print("注意: 这些示例会进行实际的网络测试，可能需要一些时间")
    print("如果网络环境不佳，某些测试可能会失败")
    
    try:
        # 运行示例（可以注释掉不需要的示例）
        await example_1_basic_usage()
        # await example_2_different_source()
        # await example_3_different_port()
        # await example_4_multiple_countries()
        # await example_5_custom_settings()
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 运行示例时发生错误: {e}")
    
    print("\n🏁 示例运行完成")

if __name__ == "__main__":
    asyncio.run(main())
