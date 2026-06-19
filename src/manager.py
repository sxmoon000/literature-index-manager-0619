"""
文献索引管理器 — Zotero/BibTeX 风格，支持分类、标签、搜索、导出

场景: 写论文时需要管理几十上百篇参考文献，手动整理太痛苦。
      用这个工具自动分类、去重、生成引用、导出 BibTeX。

技术栈:
  • BibTeX 解析/生成 (纯 Python 实现)
  • TF-IDF 自动打标签
  • 多维度搜索: 标题/作者/年份/标签
  • 云端备份 (JSON 格式)
"""
import re
import json
import csv
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from collections import Counter


# ── 数据模型 ──
@dataclass
class Reference:
    key: str              # 引用键, e.g. "smith2024mars"
    title: str
    authors: List[str]
    year: int
    journal: str = ""
    doi: str = ""
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    category: str = ""    # 自动分类: ML/NLP/CV/火箭/控制/优化...
    notes: str = ""
    read: bool = False    # 已读标记
    rating: int = 0       # 1-5
    added: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    bibtex_type: str = "article"  # article/book/inproceedings/techreport

    def to_bibtex(self) -> str:
        authors_str = " and ".join(self.authors)
        return f"""@{self.bibtex_type}{{{self.key},
  author    = {{{authors_str}}},
  title     = {{{self.title}}},
  journal   = {{{self.journal}}},
  year      = {{{self.year}}},{""
  doi       = {{{self.doi}}}," if self.doi else ""}
}}
"""

    @classmethod
    def from_dict(cls, d: dict) -> "Reference":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 索引管理器 ──
class IndexManager:
    """文献索引的增删改查 + 自动分类 + 导出"""

    CATEGORY_KEYWORDS = {
        "火箭回收": ["rocket", "landing", "vtvl", "reusable", "propulsion", "thrust", "trajectory", "火箭", "着陆"],
        "自适应控制": ["adaptive", "pid", "control", "controller", "feedback", "gain", "自适应", "控制"],
        "轨迹优化": ["trajectory", "optimization", "convex", "guidance", "ode", "optimal", "轨迹", "优化"],
        "机器学习": ["machine learning", "neural", "deep", "cnn", "lstm", "transformer", "classification", "神经网络"],
        "计算机视觉": ["vision", "image", "detection", "segmentation", "camera", "opencv", "检测", "图像"],
        "NLP": ["nlp", "language", "text", "sentiment", "tokenizer", "bert", "gpt", "自然语言"],
        "强化学习": ["reinforcement", "q-learning", "policy", "reward", "agent", "mcts", "强化"],
    }

    def __init__(self):
        self.refs: List[Reference] = []

    def add(self, ref: Reference):
        if ref.key in {r.key for r in self.refs}:
            print(f"   ⚠️  重复: {ref.key}")
            return
        ref.keywords = self._extract_keywords(ref.title + " " + ref.abstract)
        ref.category = self._classify(ref)
        self.refs.append(ref)

    def _extract_keywords(self, text: str) -> List[str]:
        """简单 TF-IDF 风格关键词提取"""
        text = re.sub(r"[^\w\s]", " ", text.lower())
        words = text.split()
        stopwords = {"the","a","an","is","are","was","were","of","in","on","to","for","and","or","with","this","that","we","our","be","been","has","have","by","from","based","using","its","it","as","at","not","but","can","also","which","new","method","proposed","approach","paper","result","results","show","shows","shown"}
        words = [w for w in words if len(w) > 3 and w not in stopwords]
        return [w for w, _ in Counter(words).most_common(8)]

    def _classify(self, ref: Reference) -> str:
        text = (ref.title + " " + ref.abstract).lower()
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw.lower() in text for kw in keywords):
                return cat
        return "其他"

    def search(self, query: str = "", category: str = "",
               year_from: int = 0, year_to: int = 9999) -> List[Reference]:
        results = self.refs.copy()
        if query:
            q = query.lower()
            results = [r for r in results if q in r.title.lower()
                       or any(q in a.lower() for a in r.authors)
                       or q in " ".join(r.keywords).lower()]
        if category:
            results = [r for r in results if r.category == category]
        results = [r for r in results if year_from <= r.year <= year_to]
        results.sort(key=lambda r: r.year, reverse=True)
        return results

    def stats(self) -> dict:
        cats = Counter(r.category for r in self.refs)
        years = Counter(r.year for r in self.refs)
        return {
            "total": len(self.refs),
            "read": sum(1 for r in self.refs if r.read),
            "avg_rating": round(sum(r.rating for r in self.refs) / max(len(self.refs), 1), 1),
            "categories": dict(cats.most_common()),
            "years": dict(sorted(years.items())),
        }

    def export_bibtex(self, path: str):
        content = "\n".join(r.to_bibtex() for r in self.refs)
        Path(path).write_text(content, encoding="utf-8")
        print(f"   BibTeX 导出: {path} ({len(self.refs)} 条)")

    def save(self, path: str = "index.json"):
        data = [asdict(r) for r in self.refs]
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str = "index.json") -> "IndexManager":
        im = cls()
        if Path(path).exists():
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            im.refs = [Reference.from_dict(d) for d in data]
        return im


# ── 演示 ──
def main():
    print("=" * 55)
    print("📚 文献索引管理器 — 分类/标签/BibTeX导出")
    print("=" * 55)

    im = IndexManager()

    # 添加文献
    samples = [
        Reference("smith2024mars", "Adaptive PID Control for Mars Landing Vehicles",
                  ["J. Smith", "L. Chen"], 2024, "J. Guidance & Control",
                  abstract="This paper presents an adaptive PID controller for Mars entry and landing vehicles under atmospheric uncertainty"),
        Reference("wang2023vtvl", "推进剂消耗下的可重复使用火箭VTVL着陆制导",
                  ["Wang M.", "Zhang L."], 2023, "宇航学报",
                  abstract="研究了燃料消耗对火箭垂直着陆段自适应PID控制性能的影响"),
        Reference("liu2025rl", "Reinforcement Learning for Rocket Landing Trajectory Optimization",
                  ["Liu H.", "Park S."], 2025, "AIAA Journal",
                  abstract="We apply deep Q-learning to optimize reusable rocket landing trajectories with fuel constraints"),
        Reference("kim2024cnn", "CNN-based Real-time Object Detection for Autonomous Landing",
                  ["Kim J.", "Brown A."], 2024, "CVPR 2024",
                  abstract="A lightweight CNN architecture for real-time landing site detection from onboard cameras"),
        Reference("zhou2025nlp", "BERT-based Sentiment Analysis of Space Mission Reports",
                  ["Zhou X."], 2025, "ACL 2025",
                  abstract="Using BERT for sentiment analysis on NASA mission reports"),
    ]
    for ref in samples:
        im.add(ref)

    # 统计
    st = im.stats()
    print(f"\n📊 统计:")
    print(f"   总文献: {st['total']}, 已读: {st['read']}/{st['total']}")
    print(f"   分类: {st['categories']}")
    print(f"   年份分布: {st['years']}")

    # 搜索
    print(f"\n🔍 搜索: 「自适应控制」")
    for r in im.search(category="自适应控制"):
        print(f"   [{r.year}] {r.title[:50]}... — {', '.join(r.authors[:2])}")

    print(f"\n🔍 搜索: 2024-2025 火箭相关")
    for r in im.search(query="rocket", year_from=2024):
        print(f"   [{r.year}] {r.title[:50]}... — {r.keywords[:4]}")

    # 导出
    im.export_bibtex("/tmp/references.bib")
    im.save("/tmp/index.json")
    print(f"\n✅ 完成!")


if __name__ == "__main__":
    main()
