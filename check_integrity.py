#!/usr/bin/env python3
"""
Clash兼容代理服务器项目完整性检查脚本
检查所有必需文件和代码完整性
"""

import os
import sys
import ast
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Any

class IntegrityChecker:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = []
        self.errors = []
        self.warnings = []
        
    def log_result(self, category: str, item: str, status: str, details: str = ""):
        """记录检查结果"""
        result = {
            'category': category,
            'item': item,
            'status': status,
            'details': details
        }
        self.results.append(result)
        
        status_icon = {
            'PASS': '✅',
            'FAIL': '❌', 
            'WARN': '⚠️',
            'INFO': 'ℹ️'
        }.get(status, '📝')
        
        print(f"{status_icon} [{category}] {item}: {details}")
        
        if status == 'FAIL':
            self.errors.append(result)
        elif status == 'WARN':
            self.warnings.append(result)
    
    def check_file_exists(self, file_path: str, required: bool = True) -> bool:
        """检查文件是否存在"""
        full_path = self.project_root / file_path
        exists = full_path.exists()
        
        if exists:
            size = full_path.stat().st_size
            self.log_result(
                'FILE', file_path, 'PASS', 
                f"存在 ({size} bytes)"
            )
        else:
            status = 'FAIL' if required else 'WARN'
            self.log_result(
                'FILE', file_path, status, 
                "不存在" + ("（必需）" if required else "（可选）")
            )
        
        return exists
    
    def check_python_syntax(self, file_path: str) -> bool:
        """检查Python文件语法"""
        full_path = self.project_root / file_path
        
        if not full_path.exists():
            return False
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查语法
            ast.parse(content)
            
            # 统计代码行数
            lines = len([line for line in content.split('\n') if line.strip() and not line.strip().startswith('#')])
            
            self.log_result(
                'SYNTAX', file_path, 'PASS',
                f"语法正确 ({lines} 行代码)"
            )
            return True
            
        except SyntaxError as e:
            self.log_result(
                'SYNTAX', file_path, 'FAIL',
                f"语法错误: {e.msg} (行 {e.lineno})"
            )
            return False
        except Exception as e:
            self.log_result(
                'SYNTAX', file_path, 'FAIL',
                f"检查失败: {e}"
            )
            return False
    
    def check_yaml_syntax(self, file_path: str) -> bool:
        """检查YAML文件语法"""
        full_path = self.project_root / file_path
        
        if not full_path.exists():
            return False
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self.log_result(
                'YAML', file_path, 'PASS',
                f"格式正确 ({len(str(data))} 字符)"
            )
            return True
            
        except yaml.YAMLError as e:
            self.log_result(
                'YAML', file_path, 'FAIL',
                f"格式错误: {e}"
            )
            return False
        except Exception as e:
            self.log_result(
                'YAML', file_path, 'FAIL',
                f"检查失败: {e}"
            )
            return False
    
    def check_imports(self, file_path: str) -> bool:
        """检查Python文件的导入依赖"""
        full_path = self.project_root / file_path
        
        if not full_path.exists():
            return False
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # 检查关键导入
            critical_imports = {
                'server.py': ['asyncio', 'yaml', 'logging'],
                'protocols/shadowsocks_server.py': ['asyncio', 'cryptography'],
                'protocols/socks5_server.py': ['asyncio', 'struct'],
                'protocols/http_server.py': ['asyncio', 'base64'],
                'utils/stats.py': ['threading', 'time'],
                'management/web_dashboard.py': ['aiohttp', 'jinja2']
            }
            
            if file_path in critical_imports:
                missing = []
                for required in critical_imports[file_path]:
                    if not any(required in imp for imp in imports):
                        missing.append(required)
                
                if missing:
                    self.log_result(
                        'IMPORT', file_path, 'WARN',
                        f"缺少关键导入: {', '.join(missing)}"
                    )
                else:
                    self.log_result(
                        'IMPORT', file_path, 'PASS',
                        f"导入完整 ({len(imports)} 个模块)"
                    )
            
            return True
            
        except Exception as e:
            self.log_result(
                'IMPORT', file_path, 'FAIL',
                f"检查失败: {e}"
            )
            return False
    
    def check_config_completeness(self) -> bool:
        """检查配置文件完整性"""
        config_file = self.project_root / 'config.yaml'
        
        if not config_file.exists():
            self.log_result('CONFIG', 'config.yaml', 'FAIL', "配置文件不存在")
            return False
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 检查必需的配置节
            required_sections = [
                'server',
                'shadowsocks', 
                'socks5',
                'http',
                'dashboard'
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in config:
                    missing_sections.append(section)
            
            if missing_sections:
                self.log_result(
                    'CONFIG', 'config.yaml', 'WARN',
                    f"缺少配置节: {', '.join(missing_sections)}"
                )
            else:
                self.log_result(
                    'CONFIG', 'config.yaml', 'PASS',
                    f"配置完整 ({len(config)} 个节)"
                )
            
            # 检查关键配置项
            if 'shadowsocks' in config and config['shadowsocks'].get('enabled'):
                ss_config = config['shadowsocks']
                if ss_config.get('password') in ['your-password', 'test-password', '']:
                    self.log_result(
                        'CONFIG', 'shadowsocks.password', 'WARN',
                        "使用默认密码，建议修改"
                    )
            
            return True
            
        except Exception as e:
            self.log_result('CONFIG', 'config.yaml', 'FAIL', f"检查失败: {e}")
            return False
    
    def check_requirements(self) -> bool:
        """检查依赖文件"""
        req_file = self.project_root / 'requirements.txt'
        
        if not req_file.exists():
            self.log_result('DEPS', 'requirements.txt', 'FAIL', "依赖文件不存在")
            return False
        
        try:
            with open(req_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 统计依赖包数量
            packages = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            
            # 检查关键依赖
            critical_deps = [
                'asyncio', 'aiohttp', 'PyYAML', 'cryptography'
            ]
            
            missing_deps = []
            for dep in critical_deps:
                if not any(dep.lower() in pkg.lower() for pkg in packages):
                    missing_deps.append(dep)
            
            if missing_deps:
                self.log_result(
                    'DEPS', 'requirements.txt', 'WARN',
                    f"缺少关键依赖: {', '.join(missing_deps)}"
                )
            else:
                self.log_result(
                    'DEPS', 'requirements.txt', 'PASS',
                    f"依赖完整 ({len(packages)} 个包)"
                )
            
            return True
            
        except Exception as e:
            self.log_result('DEPS', 'requirements.txt', 'FAIL', f"检查失败: {e}")
            return False
    
    def check_directory_structure(self) -> bool:
        """检查目录结构"""
        required_dirs = [
            'protocols',
            'utils', 
            'management'
        ]
        
        all_exist = True
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                file_count = len(list(dir_path.glob('*.py')))
                self.log_result(
                    'DIR', dir_name, 'PASS',
                    f"存在 ({file_count} 个Python文件)"
                )
            else:
                self.log_result('DIR', dir_name, 'FAIL', "目录不存在")
                all_exist = False
        
        return all_exist
    
    def run_full_check(self) -> Dict[str, Any]:
        """运行完整检查"""
        print("🔍 开始Clash兼容代理服务器项目完整性检查")
        print("=" * 60)
        
        # 检查目录结构
        print("\n📁 检查目录结构...")
        self.check_directory_structure()
        
        # 检查核心文件
        print("\n📄 检查核心文件...")
        core_files = [
            ('server.py', True),
            ('config.yaml', True),
            ('requirements.txt', True),
            ('deploy.sh', True),
            ('test_server.py', True),
            ('README.md', True),
            ('DEPLOYMENT_GUIDE.md', True),
            ('COMPLETE_DEPLOYMENT_GUIDE.md', True)
        ]
        
        for file_path, required in core_files:
            self.check_file_exists(file_path, required)
        
        # 检查协议实现文件
        print("\n🔌 检查协议实现...")
        protocol_files = [
            'protocols/__init__.py',
            'protocols/shadowsocks_server.py',
            'protocols/socks5_server.py', 
            'protocols/http_server.py',
            'protocols/vmess_server.py',
            'protocols/trojan_server.py'
        ]
        
        for file_path in protocol_files:
            if self.check_file_exists(file_path):
                self.check_python_syntax(file_path)
                self.check_imports(file_path)
        
        # 检查工具模块
        print("\n🛠️ 检查工具模块...")
        util_files = [
            'utils/__init__.py',
            'utils/stats.py'
        ]
        
        for file_path in util_files:
            if self.check_file_exists(file_path):
                self.check_python_syntax(file_path)
                self.check_imports(file_path)
        
        # 检查管理模块
        print("\n📊 检查管理模块...")
        mgmt_files = [
            'management/__init__.py',
            'management/web_dashboard.py'
        ]
        
        for file_path in mgmt_files:
            if self.check_file_exists(file_path):
                self.check_python_syntax(file_path)
                self.check_imports(file_path)
        
        # 检查主程序
        print("\n🚀 检查主程序...")
        if self.check_file_exists('server.py'):
            self.check_python_syntax('server.py')
            self.check_imports('server.py')
        
        # 检查配置文件
        print("\n⚙️ 检查配置文件...")
        if self.check_file_exists('config.yaml'):
            self.check_yaml_syntax('config.yaml')
            self.check_config_completeness()
        
        # 检查依赖文件
        print("\n📦 检查依赖文件...")
        self.check_requirements()
        
        # 生成报告
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """生成检查报告"""
        print("\n" + "=" * 60)
        print("📊 完整性检查报告")
        print("=" * 60)
        
        total_checks = len(self.results)
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        failed = len(self.errors)
        warnings = len(self.warnings)
        
        print(f"总检查项: {total_checks}")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} ❌")
        print(f"警告: {warnings} ⚠️")
        print(f"成功率: {passed/total_checks*100:.1f}%")
        
        if self.errors:
            print(f"\n❌ 发现 {len(self.errors)} 个错误:")
            for error in self.errors:
                print(f"  - [{error['category']}] {error['item']}: {error['details']}")
        
        if self.warnings:
            print(f"\n⚠️ 发现 {len(self.warnings)} 个警告:")
            for warning in self.warnings:
                print(f"  - [{warning['category']}] {warning['item']}: {warning['details']}")
        
        # 项目完整性评估
        if failed == 0:
            if warnings == 0:
                print(f"\n🎉 项目完整性: 优秀 (100%)")
                print("✅ 所有文件和代码都完整无误，可以直接部署使用！")
            else:
                print(f"\n👍 项目完整性: 良好 ({(passed/(passed+warnings))*100:.1f}%)")
                print("✅ 核心功能完整，建议处理警告项后部署。")
        else:
            print(f"\n⚠️ 项目完整性: 需要修复 ({passed/total_checks*100:.1f}%)")
            print("❌ 发现关键问题，请修复后再部署。")
        
        report = {
            'timestamp': __import__('time').time(),
            'total_checks': total_checks,
            'passed': passed,
            'failed': failed,
            'warnings': warnings,
            'success_rate': passed/total_checks*100,
            'errors': self.errors,
            'warnings': self.warnings,
            'all_results': self.results
        }
        
        # 保存报告
        try:
            import json
            with open('integrity_report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n📄 详细报告已保存: integrity_report.json")
        except Exception as e:
            print(f"\n⚠️ 报告保存失败: {e}")
        
        return report

def main():
    """主函数"""
    checker = IntegrityChecker()
    report = checker.run_full_check()
    
    # 返回适当的退出码
    if report['failed'] > 0:
        sys.exit(1)  # 有错误
    elif report['warnings'] > 0:
        sys.exit(2)  # 有警告
    else:
        sys.exit(0)  # 完全正常

if __name__ == "__main__":
    main()