#!/usr/bin/env python3
"""
Cloudflare IP优选脚本 - 获取特定国家IP数量
基于原始JavaScript bestIP功能改写
"""

import asyncio
import aiohttp
import json
import random
import ipaddress
import time
import argparse
import sys
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class IPResult:
    """IP测试结果数据类"""
    ip: str
    port: int
    latency: float
    colo: str
    country: str
    type: str  # 'official' or 'proxy'
    
    def to_display_format(self) -> str:
        """转换为显示格式"""
        type_text = "官方优选" if self.type == "official" else "反代优选"
        return f"{self.ip}:{self.port}#{self.country} {type_text} {self.latency:.0f}ms"

class CloudflareIPOptimizer:
    """Cloudflare IP优选器"""
    
    def __init__(self, target_country: str = "CN", max_ips: int = 512, max_concurrent: int = 32, target_count: int = 10):
        self.target_country = target_country.upper()
        self.max_ips = max_ips
        self.max_concurrent = max_concurrent
        self.target_count = target_count  # 目标IP数量
        self.nip_domain = "ip.090227.xyz"  # 默认域名
        self.session: Optional[aiohttp.ClientSession] = None

        # 定义所有可用的IP源，按优先级排序
        self.ip_sources = [
            "official",    # CF官方列表（优先级最高）
            "cm",          # CM整理列表
            "as13335",     # AS13335 CF全段
            "as209242",    # AS209242 CF非官方
            "proxyip",     # 反代IP列表
            "as24429",     # AS24429 Alibaba
            "as35916",     # AS35916
            "as199524",    # AS199524 G-Core
        ]
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=50)
        )
        await self._get_nip_domain()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def _get_nip_domain(self) -> None:
        """获取NIP域名"""
        try:
            dns_query_url = "https://cloudflare-dns.com/dns-query?name=nip.090227.xyz&type=TXT"
            headers = {'Accept': 'application/dns-json'}
            
            async with self.session.get(dns_query_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('Status') == 0 and data.get('Answer'):
                        txt_record = data['Answer'][0]['data']
                        self.nip_domain = txt_record.strip('"')
                        print(f"通过DoH解析获取到域名: {self.nip_domain}")
                        return
        except Exception as e:
            print(f"DoH解析失败，使用默认域名: {e}")
        
        # 备用域名
        self.nip_domain = "nip.lfree.org"
    
    async def get_cf_ips(self, ip_source: str = "official", target_port: str = "443") -> List[str]:
        """获取Cloudflare IP列表"""
        print(f"正在获取 {ip_source} IP列表...")
        
        try:
            if ip_source == "as13335":
                url = "https://raw.githubusercontent.com/ipverse/asn-ip/master/as/13335/ipv4-aggregated.txt"
            elif ip_source == "as209242":
                url = "https://raw.githubusercontent.com/ipverse/asn-ip/master/as/209242/ipv4-aggregated.txt"
            elif ip_source == "as24429":
                url = "https://raw.githubusercontent.com/ipverse/asn-ip/master/as/24429/ipv4-aggregated.txt"
            elif ip_source == "as35916":
                url = "https://raw.githubusercontent.com/ipverse/asn-ip/master/as/35916/ipv4-aggregated.txt"
            elif ip_source == "as199524":
                url = "https://raw.githubusercontent.com/ipverse/asn-ip/master/as/199524/ipv4-aggregated.txt"
            elif ip_source == "cm":
                url = "https://raw.githubusercontent.com/cmliu/cmliu/main/CF-CIDR.txt"
            elif ip_source == "proxyip":
                return await self._get_proxy_ips(target_port)
            else:  # official
                url = "https://www.cloudflare.com/ips-v4/"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                else:
                    # 使用默认CIDR列表
                    text = """173.245.48.0/20
103.21.244.0/22
103.22.200.0/22
103.31.4.0/22
141.101.64.0/18
108.162.192.0/18
190.93.240.0/20
188.114.96.0/20
197.234.240.0/22
198.41.128.0/17
162.158.0.0/15
104.16.0.0/13
104.24.0.0/14
172.64.0.0/13
131.0.72.0/22"""
            
            cidrs = [line.strip() for line in text.split('\n') if line.strip() and not line.startswith('#')]
            return self._generate_ips_from_cidrs(cidrs)
            
        except Exception as e:
            print(f"获取CF IPs失败: {e}")
            return []
    
    async def _get_proxy_ips(self, target_port: str) -> List[str]:
        """获取反代IP列表"""
        try:
            url = "https://raw.githubusercontent.com/cmliu/ACL4SSR/main/baipiao.txt"
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                text = await response.text()
                lines = [line.strip() for line in text.split('\n') 
                        if line.strip() and not line.startswith('#')]
                
                valid_ips = []
                for line in lines:
                    parsed_ip = self._parse_proxy_ip_line(line, target_port)
                    if parsed_ip:
                        valid_ips.append(parsed_ip)
                
                print(f"反代IP列表解析完成，端口{target_port}匹配到{len(valid_ips)}个有效IP")
                
                # 如果超过512个IP，随机选择512个
                if len(valid_ips) > self.max_ips:
                    valid_ips = random.sample(valid_ips, self.max_ips)
                    print(f"IP数量超过{self.max_ips}个，随机选择了{len(valid_ips)}个IP")
                
                return valid_ips
                
        except Exception as e:
            print(f"获取反代IP失败: {e}")
            return []
    
    def _parse_proxy_ip_line(self, line: str, target_port: str) -> Optional[str]:
        """解析反代IP行"""
        try:
            line = line.strip()
            if not line:
                return None
            
            ip = ""
            port = ""
            comment = ""
            
            # 处理注释部分
            if '#' in line:
                parts = line.split('#', 1)
                main_part = parts[0].strip()
                comment = parts[1].strip()
            else:
                main_part = line
            
            # 处理端口部分
            if ':' in main_part:
                ip_port_parts = main_part.split(':')
                if len(ip_port_parts) == 2:
                    ip = ip_port_parts[0].strip()
                    port = ip_port_parts[1].strip()
                else:
                    return None
            else:
                ip = main_part
                port = "443"
            
            # 验证IP格式
            if not self._is_valid_ip(ip):
                return None
            
            # 验证端口格式
            try:
                port_num = int(port)
                if port_num < 1 or port_num > 65535:
                    return None
            except ValueError:
                return None
            
            # 检查端口是否匹配
            if port != target_port:
                return None
            
            # 构建返回格式
            if comment:
                return f"{ip}:{port}#{comment}"
            else:
                return f"{ip}:{port}"
                
        except Exception:
            return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        try:
            ipaddress.IPv4Address(ip)
            return True
        except ipaddress.AddressValueError:
            return False
    
    def _generate_ips_from_cidrs(self, cidrs: List[str]) -> List[str]:
        """从CIDR列表生成IP"""
        ips = set()
        target_count = self.max_ips
        round_num = 1
        
        while len(ips) < target_count and round_num <= 100:
            print(f"第{round_num}轮生成IP，当前已有{len(ips)}个")
            
            for cidr in cidrs:
                if len(ips) >= target_count:
                    break
                
                cidr_ips = self._generate_ips_from_cidr(cidr.strip(), round_num)
                ips.update(cidr_ips)
                
                print(f"CIDR {cidr} 第{round_num}轮生成{len(cidr_ips)}个IP，总计{len(ips)}个")
            
            round_num += 1
        
        print(f"最终生成{len(ips)}个不重复IP")
        return list(ips)[:target_count]
    
    def _generate_ips_from_cidr(self, cidr: str, count: int = 1) -> List[str]:
        """从单个CIDR生成IP"""
        try:
            network = ipaddress.IPv4Network(cidr, strict=False)
            max_hosts = network.num_addresses - 2  # 排除网络地址和广播地址
            
            if max_hosts <= 0:
                return []
            
            actual_count = min(count, max_hosts)
            ips = set()
            
            attempts = 0
            max_attempts = actual_count * 10
            
            while len(ips) < actual_count and attempts < max_attempts:
                # 生成随机偏移量，避免网络地址
                random_offset = random.randint(1, max_hosts)
                random_ip = str(network.network_address + random_offset)
                ips.add(random_ip)
                attempts += 1
            
            return list(ips)

        except Exception as e:
            print(f"生成CIDR {cidr} IP失败: {e}")
            return []

    async def test_ip(self, ip: str, port: int) -> Optional[IPResult]:
        """测试单个IP"""
        timeout = 5.0

        # 解析IP格式
        parsed_ip = self._parse_ip_format(ip, port)
        if not parsed_ip:
            return None

        # 进行测试，最多重试3次
        for attempt in range(1, 4):
            result = await self._single_test(parsed_ip['host'], parsed_ip['port'], timeout)
            if result:
                print(f"IP {parsed_ip['host']}:{parsed_ip['port']} 第{attempt}次测试成功: {result['latency']:.0f}ms, colo: {result['colo']}")

                # 获取国家代码
                country_code = await self._get_country_from_colo(result['colo'])

                # 生成显示格式
                type_text = "官方优选" if result['type'] == "official" else "反代优选"

                return IPResult(
                    ip=parsed_ip['host'],
                    port=parsed_ip['port'],
                    latency=result['latency'],
                    colo=result['colo'],
                    country=country_code,
                    type=result['type']
                )
            else:
                print(f"IP {parsed_ip['host']}:{parsed_ip['port']} 第{attempt}次测试失败")
                if attempt < 3:
                    await asyncio.sleep(0.2)  # 短暂延迟后重试

        return None

    def _parse_ip_format(self, ip_string: str, default_port: int) -> Optional[Dict]:
        """解析IP格式"""
        try:
            host = ""
            port = default_port
            comment = ""

            # 处理注释部分（#之后的内容）
            main_part = ip_string
            if '#' in ip_string:
                parts = ip_string.split('#', 1)
                main_part = parts[0]
                comment = parts[1]

            # 处理端口部分
            if ':' in main_part:
                parts = main_part.split(':')
                host = parts[0]
                try:
                    port = int(parts[1])
                except ValueError:
                    return None
            else:
                host = main_part

            # 验证IP格式
            if not host or not self._is_valid_ip(host.strip()):
                return None

            return {
                'host': host.strip(),
                'port': port,
                'comment': comment.strip() if comment else None
            }
        except Exception:
            return None

    async def _single_test(self, ip: str, port: int, timeout: float) -> Optional[Dict]:
        """单次IP测试"""
        try:
            # 构建测试URL
            parts = ip.split('.')
            hex_parts = [f"{int(part):02x}" for part in parts]
            nip = ''.join(hex_parts)
            test_url = f"https://{nip}.{self.nip_domain}:{port}/cdn-cgi/trace"

            start_time = time.time()

            async with self.session.get(test_url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                if response.status == 200:
                    latency = (time.time() - start_time) * 1000  # 转换为毫秒
                    response_text = await response.text()

                    # 解析trace响应
                    trace_data = self._parse_trace_response(response_text)

                    if trace_data and trace_data.get('ip') and trace_data.get('colo'):
                        # 判断IP类型
                        response_ip = trace_data['ip']
                        ip_type = 'official'  # 默认官方IP

                        # 检查是否是IPv6（包含冒号）或者IP相等
                        if ':' in response_ip or response_ip == ip:
                            ip_type = 'proxy'  # 反代IP

                        return {
                            'ip': ip,
                            'port': port,
                            'latency': latency,
                            'colo': trace_data['colo'],
                            'type': ip_type,
                            'response_ip': response_ip
                        }

            return None

        except Exception as e:
            return None

    def _parse_trace_response(self, response_text: str) -> Optional[Dict]:
        """解析trace响应"""
        try:
            lines = response_text.split('\n')
            data = {}

            for line in lines:
                trimmed_line = line.strip()
                if trimmed_line and '=' in trimmed_line:
                    key, value = trimmed_line.split('=', 1)
                    data[key] = value

            return data
        except Exception:
            return None

    async def _get_country_from_colo(self, colo: str) -> str:
        """从colo获取国家代码"""
        # Cloudflare colo到国家代码的映射
        colo_to_country = {
            # 中国大陆
            'SJC': 'CN', 'LAX': 'CN', 'HKG': 'CN', 'NRT': 'CN', 'ICN': 'CN',
            # 美国
            'ATL': 'US', 'BOS': 'US', 'BUF': 'US', 'CHI': 'US', 'DEN': 'US',
            'DFW': 'US', 'EWR': 'US', 'IAD': 'US', 'LAS': 'US', 'LAX': 'US',
            'MIA': 'US', 'MSP': 'US', 'ORD': 'US', 'PDX': 'US', 'PHX': 'US',
            'SAN': 'US', 'SEA': 'US', 'SJC': 'US', 'STL': 'US',
            # 日本
            'NRT': 'JP', 'KIX': 'JP',
            # 韩国
            'ICN': 'KR',
            # 香港
            'HKG': 'HK',
            # 台湾
            'TPE': 'TW',
            # 新加坡
            'SIN': 'SG',
            # 英国
            'LHR': 'GB', 'MAN': 'GB',
            # 德国
            'FRA': 'DE', 'DUS': 'DE',
            # 法国
            'CDG': 'FR', 'MRS': 'FR',
            # 荷兰
            'AMS': 'NL',
            # 澳大利亚
            'SYD': 'AU', 'MEL': 'AU', 'PER': 'AU',
            # 加拿大
            'YYZ': 'CA', 'YVR': 'CA',
            # 巴西
            'GRU': 'BR',
            # 印度
            'BOM': 'IN', 'DEL': 'IN', 'MAA': 'IN',
        }

        # 尝试从映射表获取国家代码
        country = colo_to_country.get(colo.upper())
        if country:
            return country

        # 如果映射表中没有，尝试通过Cloudflare位置API获取
        try:
            url = "https://speed.cloudflare.com/locations"
            async with self.session.get(url) as response:
                if response.status == 200:
                    locations = await response.json()
                    for location in locations:
                        if location.get('iata') == colo.upper():
                            return location.get('cca2', colo.upper())
        except Exception:
            pass

        # 如果都失败了，返回原始colo代码
        return colo.upper()

    async def test_ips_with_concurrency(self, ips: List[str], port: int) -> List[IPResult]:
        """并发测试IP列表"""
        results = []
        total_ips = len(ips)
        completed_tests = 0

        print(f"开始测试 {total_ips} 个IP，端口 {port}，并发数 {self.max_concurrent}")

        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def test_with_semaphore(ip):
            nonlocal completed_tests
            async with semaphore:
                result = await self.test_ip(ip, port)
                completed_tests += 1

                if completed_tests % 50 == 0 or completed_tests == total_ips:
                    progress = (completed_tests / total_ips) * 100
                    print(f"测试进度: {completed_tests}/{total_ips} ({progress:.1f}%) - 有效IP: {len(results)}")

                if result:
                    results.append(result)

                return result

        # 创建所有任务
        tasks = [test_with_semaphore(ip) for ip in ips]

        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def test_ips_with_early_stop(self, ips: List[str], port: int) -> List[IPResult]:
        """并发测试IP列表，找到足够的目标国家IP时提前停止"""
        results = []
        country_results = []
        total_ips = len(ips)
        completed_tests = 0

        print(f"  🧪 开始测试 {total_ips} 个IP，端口 {port}")

        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent)
        stop_event = asyncio.Event()

        async def test_with_semaphore(ip):
            nonlocal completed_tests, country_results

            # 如果已经找到足够的目标国家IP，跳过测试
            if stop_event.is_set():
                return None

            async with semaphore:
                if stop_event.is_set():
                    return None

                result = await self.test_ip(ip, port)
                completed_tests += 1

                if result:
                    results.append(result)

                    # 检查是否是目标国家的IP
                    if result.country == self.target_country:
                        country_results.append(result)

                        # 如果找到足够的目标国家IP，设置停止信号
                        if len(country_results) >= self.target_count:
                            print(f"  🎯 已找到 {len(country_results)} 个 {self.target_country} IP，停止当前库的测试")
                            stop_event.set()

                # 定期报告进度
                if completed_tests % 20 == 0 or completed_tests == total_ips:
                    progress = (completed_tests / total_ips) * 100
                    print(f"  📊 进度: {completed_tests}/{total_ips} ({progress:.1f}%) - {self.target_country} IP: {len(country_results)}")

                return result

        # 创建所有任务
        tasks = [test_with_semaphore(ip) for ip in ips]

        # 等待所有任务完成或停止信号
        await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def get_country_ips_from_all_sources(self, target_port: str = "443") -> List[IPResult]:
        """遍历所有IP库获取指定国家的IP，直到找到目标数量"""
        print(f"🌍 开始遍历所有IP库获取 {self.target_country} 国家的IP")
        print(f"🎯 目标: 找到 {self.target_count} 个 {self.target_country} 国家的IP")
        print(f"📊 配置信息: 端口={target_port}, 最大IP数={self.max_ips}, 并发数={self.max_concurrent}")
        print("-" * 60)

        all_results = []

        for i, source in enumerate(self.ip_sources, 1):
            if len(all_results) >= self.target_count:
                print(f"✅ 已找到足够的IP ({len(all_results)} 个)，停止搜索")
                break

            print(f"\n📚 [{i}/{len(self.ip_sources)}] 正在尝试 {source} IP库...")

            try:
                # 获取当前源的结果
                source_results = await self.get_country_ips_from_source(source, target_port)

                if source_results:
                    # 添加到总结果中，避免重复
                    existing_ips = {f"{r.ip}:{r.port}" for r in all_results}
                    new_results = [r for r in source_results if f"{r.ip}:{r.port}" not in existing_ips]

                    all_results.extend(new_results)
                    print(f"✅ 从 {source} 获得 {len(new_results)} 个新的 {self.target_country} IP")
                    print(f"📊 当前总计: {len(all_results)} 个IP")

                    # 如果已经找到足够的IP，可以提前结束
                    if len(all_results) >= self.target_count:
                        print(f"🎉 已达到目标数量 ({self.target_count} 个)！")
                        break
                else:
                    print(f"❌ {source} 库未找到任何 {self.target_country} IP")

            except Exception as e:
                print(f"❌ {source} 库处理失败: {e}")
                continue

        # 按延迟排序并限制数量
        all_results.sort(key=lambda x: x.latency)
        final_results = all_results[:self.target_count]

        print(f"\n" + "=" * 60)
        print(f"🏁 搜索完成！")
        print(f"📊 最终结果: 找到 {len(final_results)} 个 {self.target_country} 国家的优质IP")

        if final_results:
            print(f"⚡ 延迟范围: {final_results[0].latency:.0f}ms - {final_results[-1].latency:.0f}ms")
            avg_latency = sum(r.latency for r in final_results) / len(final_results)
            print(f"⚡ 平均延迟: {avg_latency:.0f}ms")

        return final_results

    async def get_country_ips_from_source(self, ip_source: str, target_port: str = "443") -> List[IPResult]:
        """从单个IP源获取特定国家的IP"""
        try:
            # 获取IP列表
            ips = await self.get_cf_ips(ip_source, target_port)
            if not ips:
                return []

            print(f"  📥 获取到 {len(ips)} 个IP，开始测试...")

            # 测试IP，但是一旦找到足够的目标国家IP就停止
            results = await self.test_ips_with_early_stop(ips, int(target_port))

            if not results:
                return []

            # 筛选目标国家的IP
            country_results = [r for r in results if r.country == self.target_country]

            # 按延迟排序
            country_results.sort(key=lambda x: x.latency)

            return country_results

        except Exception as e:
            print(f"  ❌ 处理 {ip_source} 时发生错误: {e}")
            return []

    def save_results_to_file(self, results: List[IPResult], filename: str = "nodes.txt") -> None:
        """保存结果到文件"""
        try:
            output_path = Path(filename)

            # 生成内容
            lines = []
            for result in results:
                lines.append(result.to_display_format())

            # 写入文件（覆盖模式）
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            print(f"成功保存 {len(results)} 个节点到 {filename}")

        except Exception as e:
            print(f"保存文件失败: {e}")

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Cloudflare IP优选脚本 - 遍历所有IP库获取指定国家IP')
    parser.add_argument('--country', '-c', default='CN', help='目标国家代码 (默认: CN)')
    parser.add_argument('--count', '-n', type=int, default=10, help='目标IP数量 (默认: 10)')
    parser.add_argument('--port', '-p', default='443', help='目标端口 (默认: 443)')
    parser.add_argument('--max-ips', '-m', type=int, default=512, help='每个库最大IP数量 (默认: 512)')
    parser.add_argument('--concurrent', type=int, default=32, help='并发数 (默认: 32)')
    parser.add_argument('--output', '-o', default='nodes.txt', help='输出文件名 (默认: nodes.txt)')

    args = parser.parse_args()

    print(f"🚀 Cloudflare IP优选脚本启动")
    print(f"🎯 目标: 找到 {args.count} 个 {args.country} 国家的IP")
    print(f"📊 配置信息:")
    print(f"   - 目标国家: {args.country}")
    print(f"   - 目标数量: {args.count}")
    print(f"   - 端口: {args.port}")
    print(f"   - 每库最大IP数: {args.max_ips}")
    print(f"   - 并发数: {args.concurrent}")
    print(f"   - 输出文件: {args.output}")
    print("=" * 60)

    try:
        async with CloudflareIPOptimizer(
            target_country=args.country,
            max_ips=args.max_ips,
            max_concurrent=args.concurrent,
            target_count=args.count
        ) as optimizer:

            # 遍历所有IP库获取特定国家的IP
            results = await optimizer.get_country_ips_from_all_sources(args.port)

            if results:
                # 保存结果到文件
                optimizer.save_results_to_file(results, args.output)

                # 显示统计信息
                print("\n" + "=" * 60)
                print("📊 最终统计:")
                print(f"✅ 成功找到 {len(results)} 个 {args.country} 国家的优质IP")
                if results:
                    print(f"⚡ 延迟范围: {results[0].latency:.0f}ms - {results[-1].latency:.0f}ms")
                    print(f"⚡ 平均延迟: {sum(r.latency for r in results) / len(results):.0f}ms")

                # 显示所有找到的IP
                print(f"\n🏆 优选IP列表:")
                for i, result in enumerate(results, 1):
                    print(f"{i:2d}. {result.to_display_format()}")

                print(f"\n💾 结果已保存到: {args.output}")

            else:
                print(f"❌ 遍历所有IP库后，未找到任何 {args.country} 国家的有效IP")
                print("💡 建议:")
                print("   1. 检查网络连接")
                print("   2. 尝试其他国家代码")
                print("   3. 增加并发数或每库IP数量")

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
