#!/usr/bin/env python3

import asyncio
import re
import yaml
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from rich.console import Console
from rich.table import Table
import aiohttp
import markdown
from urllib.parse import urlparse, urljoin
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from collections import defaultdict

@dataclass
class LinkContext:
    text: str  # Link text or alt text for images
    url: str   # The actual URL
    context: str  # Surrounding text/context
    line_number: int  # Line number in file
    is_image: bool = False

@dataclass
class DocumentInfo:
    path: Path
    title: str
    links: List[LinkContext] = field(default_factory=list)
    missing_links: List[dict] = field(default_factory=list)

@dataclass
class LinkValidationResult:
    link: LinkContext
    is_valid: bool
    error_message: Optional[str] = None
    status_code: Optional[int] = None

class DocLinkChecker:
    def __init__(self, docs_root: Path):
        self.docs_root = Path(docs_root).resolve()
        self.project_root = self.docs_root.parent  # 项目根目录
        self.static_img_dir = self.project_root / 'static' / 'img' / 'docs'  # 静态图片目录
        self.console = Console()
        self.documents: Dict[Path, DocumentInfo] = {}
        self.ignore_patterns: Set[str] = set()
        self.load_ignore_patterns()
        
        # 用于统计的变量
        self.missing_images = defaultdict(set)
        self.timeout_links = defaultdict(set)
        self.invalid_format_links = defaultdict(set)
        self.empty_links = defaultdict(set)
        self.suggested_links = defaultdict(list)

    def load_ignore_patterns(self):
        ignore_file = self.docs_root / '.ignore'
        if ignore_file.exists():
            self.ignore_patterns = set(ignore_file.read_text().splitlines())

    def extract_front_matter(self, content: str) -> tuple[str, Optional[str]]:
        """Extract YAML front matter and return (content, title)"""
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    front_matter = yaml.safe_load(parts[1])
                    return parts[2], front_matter.get('title')
                except yaml.YAMLError:
                    return content, None
        return content, None

    def extract_title(self, content: str) -> str:
        """Extract title from content (# Title or YAML front matter)"""
        content, yaml_title = self.extract_front_matter(content)
        if yaml_title:
            return yaml_title
        
        # Look for # Title
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "Untitled"

    def extract_links(self, content: str) -> List[LinkContext]:
        links = []
        # Regular Markdown links [text](url)
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', content):
            text, url = match.groups()
            context = self.get_context(content, match.start())
            links.append(LinkContext(text, url, context, content[:match.start()].count('\n') + 1))

        # Image links ![alt](url)
        for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', content):
            text, url = match.groups()
            context = self.get_context(content, match.start())
            links.append(LinkContext(text, url, context, content[:match.start()].count('\n') + 1, True))

        # Raw URLs <url>
        for match in re.finditer(r'<(https?://[^>]+)>', content):
            url = match.group(1)
            context = self.get_context(content, match.start())
            links.append(LinkContext(url, url, context, content[:match.start()].count('\n') + 1))

        return links

    def get_context(self, content: str, pos: int, context_chars: int = 100) -> str:
        """Get surrounding context for a link position"""
        start = max(0, pos - context_chars)
        end = min(len(content), pos + context_chars)
        return content[start:end].strip()

    def detect_missing_links(self, content: str, doc_path: Path) -> List[dict]:
        missing = []
        
        # Check for "see X" or "refer to X" without links
        patterns = [
            r'(?:see|refer to|check|consult)\s+([A-Z][a-zA-Z\s]+)(?!\])',  # Capitalized terms
            r'`([^`]+)`\s+(?:method|function|API|endpoint)',  # Code references
            r'[vV]ersion\s+(\d+\.\d+)',  # Version references
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                term = match.group(1)
                context = self.get_context(content, match.start())
                missing.append({
                    'term': term,
                    'context': context,
                    'line': content[:match.start()].count('\n') + 1,
                    'suggestion': self.suggest_link(term, doc_path)
                })

        return missing

    def suggest_link(self, term: str, doc_path: Path) -> str:
        """Suggest a link target for a term"""
        # This is a simplified version - you might want to implement more sophisticated suggestions
        if term.startswith(('get', 'post', 'put', 'delete')):
            return f"API reference for `{term}`"
        elif re.match(r'\d+\.\d+', term):
            return "Version history"
        else:
            return f"Documentation for {term}"

    async def check_external_link(self, url: str) -> tuple[bool, Optional[str], Optional[int]]:
        """Check if an external URL is accessible"""
        if not url.startswith(('http://', 'https://')):
            return False, "Invalid URL format", None

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    return response.status < 400, None, response.status
        except asyncio.TimeoutError:
            return False, "Timeout", None
        except aiohttp.ClientError as e:
            return False, str(e), None

    def check_local_link(self, url: str, doc_path: Path) -> tuple[bool, Optional[str]]:
        """Check if a local file or anchor exists"""
        if url.startswith('#'):
            return True, None  # Anchors are validated separately
        
        try:
            # 处理图片链接
            if url.startswith('/img/docs/'):
                # 将 /img/docs/ 路径映射到 static/img/docs/
                img_path = self.static_img_dir / Path(url).relative_to('/img/docs')
                return img_path.exists(), None if img_path.exists() else f"Image not found in static directory: {img_path}"
            
            # 处理其他本地文件链接
            target_path = (doc_path.parent / url).resolve()
            return target_path.exists(), None if target_path.exists() else "File not found"
        except Exception as e:
            return False, str(e)

    async def validate_links(self, doc_info: DocumentInfo) -> List[LinkValidationResult]:
        results = []
        for link in doc_info.links:
            if any(pattern in link.url for pattern in self.ignore_patterns):
                continue

            url = link.url.split('#')[0]  # Remove anchor
            if not url or url == '#':
                self.empty_links[doc_info.path].add(link.url)
                results.append(LinkValidationResult(link, False, "Empty link"))
                continue

            if url.startswith(('http://', 'https://')):
                is_valid, error, status = await self.check_external_link(url)
                if not is_valid:
                    if error == "Timeout":
                        self.timeout_links[doc_info.path].add(url)
                    else:
                        self.invalid_format_links[doc_info.path].add(url)
                results.append(LinkValidationResult(link, is_valid, error, status))
            else:
                is_valid, error = self.check_local_link(url, doc_info.path)
                if not is_valid and link.is_image:
                    if url.startswith('/img/docs/'):
                        # 记录相对于 static/img/docs 的路径
                        img_path = Path(url).relative_to('/img/docs')
                        self.missing_images[doc_info.path].add(str(img_path))
                results.append(LinkValidationResult(link, is_valid, error))

        # 处理建议的链接
        for missing in doc_info.missing_links:
            self.suggested_links[doc_info.path].append({
                'term': missing['term'],
                'suggestion': missing['suggestion'],
                'context': missing['context']
            })

        return results

    async def process_document(self, path: Path):
        """Process a single markdown document"""
        try:
            content = path.read_text(encoding='utf-8')
            title = self.extract_title(content)
            links = self.extract_links(content)
            missing = self.detect_missing_links(content, path)

            doc_info = DocumentInfo(path, title, links, missing)
            self.documents[path] = doc_info

            return await self.validate_links(doc_info)
        except Exception as e:
            self.console.print(f"[red]Error processing {path}: {str(e)}[/red]")
            return []

    async def scan_docs(self):
        """Scan all markdown files in the docs directory"""
        try:
            if not self.docs_root.exists():
                self.console.print(f"[red]Error: Directory '{self.docs_root}' does not exist![/red]")
                return []
            
            markdown_files = list(self.docs_root.rglob('*.md'))
            if not markdown_files:
                self.console.print(f"[yellow]Warning: No markdown files found in '{self.docs_root}'[/yellow]")
                return []
            
            self.console.print(f"[green]Found {len(markdown_files)} markdown files.[/green]")
            tasks = [self.process_document(path) for path in markdown_files]
            return await asyncio.gather(*tasks)
        except Exception as e:
            self.console.print(f"[red]Error scanning docs: {str(e)}[/red]")
            return []

    def generate_report(self, validation_results: List[List[LinkValidationResult]]):
        """Generate a comprehensive report of link validation results"""
        console = Console()
        
        if not self.documents:
            console.print("[yellow]No documents were processed. Please check if the docs directory exists and contains .md files.[/yellow]")
            return

        # Summary table
        summary = Table(title="Link Validation Summary")
        summary.add_column("Document")
        summary.add_column("Total Links")
        summary.add_column("Valid")
        summary.add_column("Invalid")
        summary.add_column("Missing Suggestions")

        for doc_path, results in zip(self.documents.keys(), validation_results):
            valid = sum(1 for r in results if r.is_valid)
            total = len(results)
            missing = len(self.documents[doc_path].missing_links)
            summary.add_row(
                str(doc_path.relative_to(self.docs_root)),
                str(total),
                str(valid),
                str(total - valid),
                str(missing)
            )

        console.print(summary)
        console.print()

        # Invalid links report
        console.print("[bold red]Invalid Links Report:[/bold red]")
        for doc_path, results in zip(self.documents.keys(), validation_results):
            invalid_links = [r for r in results if not r.is_valid]
            if invalid_links:
                console.print(f"\n[bold]{doc_path.relative_to(self.docs_root)}[/bold]")
                for result in invalid_links:
                    console.print(f"  • {result.link.url}")
                    console.print(f"    Error: {result.error_message}")
                    console.print(f"    Context: \"{result.link.context}\"")
                    console.print(f"    Line: {result.link.line_number}")

        # Missing links suggestions
        console.print("\n[bold yellow]Missing Links Suggestions:[/bold yellow]")
        for doc_path, doc_info in self.documents.items():
            if doc_info.missing_links:
                console.print(f"\n[bold]{doc_path.relative_to(self.docs_root)}[/bold]")
                for missing in doc_info.missing_links:
                    console.print(f"  • Term: {missing['term']}")
                    console.print(f"    Context: \"{missing['context']}\"")
                    console.print(f"    Suggestion: {missing['suggestion']}")
                    console.print(f"    Line: {missing['line']}")

    def save_report_to_file(self, report_file: Path):
        """将检查结果保存到文件"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with report_file.open('w', encoding='utf-8') as f:
            f.write(f"# 文档链接检查报告\n\n")
            f.write(f"生成时间：{timestamp}\n\n")
            
            # 1. 图片链接问题
            f.write("## 1. 图片链接问题\n\n")
            f.write("### 1.1 缺失图片文件\n")
            f.write(f"以下图片文件未找到，需要确保它们存在于 `{self.static_img_dir}` 目录下：\n\n")
            
            for doc_path, images in sorted(self.missing_images.items()):
                if images:
                    f.write(f"#### {doc_path.relative_to(self.docs_root)}\n")
                    for img in sorted(images):
                        f.write(f"- `{img}`\n")
                    f.write("\n")
            
            # 2. 外部链接问题
            f.write("## 2. 外部链接问题\n\n")
            
            # 2.1 超时链接
            f.write("### 2.1 超时链接\n")
            f.write("以下外部链接访问超时，需要验证其可访问性：\n\n")
            for doc_path, links in sorted(self.timeout_links.items()):
                if links:
                    f.write(f"#### {doc_path.relative_to(self.docs_root)}\n")
                    for link in sorted(links):
                        f.write(f"- `{link}`\n")
                    f.write("\n")
            
            # 2.2 格式错误的链接
            f.write("### 2.2 格式错误的链接\n")
            f.write("以下链接格式不正确，需要补充完整的URL：\n\n")
            for doc_path, links in sorted(self.invalid_format_links.items()):
                if links:
                    f.write(f"#### {doc_path.relative_to(self.docs_root)}\n")
                    for link in sorted(links):
                        f.write(f"- `{link}`\n")
                    f.write("\n")
            
            # 2.3 空链接
            f.write("### 2.3 空链接\n")
            f.write("以下链接为空或只包含锚点，需要补充实际链接：\n\n")
            for doc_path, links in sorted(self.empty_links.items()):
                if links:
                    f.write(f"#### {doc_path.relative_to(self.docs_root)}\n")
                    for link in sorted(links):
                        f.write(f"- `{link}`\n")
                    f.write("\n")
            
            # 3. 建议添加的链接
            f.write("## 3. 建议添加的链接\n\n")
            for doc_path, suggestions in sorted(self.suggested_links.items()):
                if suggestions:
                    f.write(f"### {doc_path.relative_to(self.docs_root)}\n")
                    for suggestion in suggestions:
                        f.write(f"- {suggestion['term']} - {suggestion['suggestion']}\n")
                        f.write(f"  上下文：{suggestion['context']}\n")
                    f.write("\n")
            
            # 4. 统计信息
            f.write("## 4. 统计信息\n\n")
            total_files = len(self.documents)
            total_missing_images = sum(len(imgs) for imgs in self.missing_images.values())
            total_timeout_links = sum(len(links) for links in self.timeout_links.values())
            total_invalid_links = sum(len(links) for links in self.invalid_format_links.values())
            total_empty_links = sum(len(links) for links in self.empty_links.values())
            total_suggestions = sum(len(suggs) for suggs in self.suggested_links.values())
            
            f.write(f"- 检查的文件总数：{total_files}\n")
            f.write("- 发现的问题：\n")
            f.write(f"  - 缺失图片：{total_missing_images}个\n")
            f.write(f"  - 超时链接：{total_timeout_links}个\n")
            f.write(f"  - 格式错误链接：{total_invalid_links}个\n")
            f.write(f"  - 空链接：{total_empty_links}个\n")
            f.write(f"  - 建议添加链接：{total_suggestions}个\n")

async def main():
    # 获取脚本所在目录的父目录（项目根目录）
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    docs_dir = project_root / 'docs'
    report_file = script_dir / 'link_check_report.md'
    
    console = Console()
    console.print(f"[blue]Scanning docs directory: {docs_dir}[/blue]")
    
    checker = DocLinkChecker(docs_dir)
    results = await checker.scan_docs()
    checker.generate_report(results)
    
    # 保存报告到文件
    checker.save_report_to_file(report_file)
    console.print(f"[green]Report saved to: {report_file}[/green]")

if __name__ == '__main__':
    asyncio.run(main()) 