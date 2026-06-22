"""
文献阅读追踪器 — 阅读进度 + 笔记 + 引用网络

功能:
  • 阅读打卡: 开始/暂停/完成，记录阅读时间
  • 笔记系统: Markdown 格式笔记，关联到文献的特定章节
  • 引用关系图: 谁引用了谁，构建文献引用网络
  • 阅读统计: 每周阅读量、平均速度、完成率
  • 知识图谱: 根据关键词共现生成知识关联图
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
from pathlib import Path


@dataclass
class ReadingNote:
    ref_key: str
    section: str        # 关联的章节 (如 "3.2 实验结果")
    note_text: str
    note_type: str      # idea / question / summary / todo / quote
    page: str = ""
    tags: List[str] = field(default_factory=list)
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = ""


@dataclass
class ReadingSession:
    ref_key: str
    start_time: str
    end_time: str = ""
    pages_read: int = 0
    comprehension: int = 0  # 1-5 理解程度自评


@dataclass
class CitationEdge:
    source: str      # 引用的文献
    target: str      # 被引用的文献
    context: str = ""  # 引用上下文


class ReadingTracker:
    """阅读进度 + 笔记系统"""

    def __init__(self):
        self.sessions: List[ReadingSession] = []
        self.notes: List[ReadingNote] = []
        self.citations: List[CitationEdge] = []
        self.reading_goals: Dict[str, int] = {}  # {"week": 目标页数}

    def start_reading(self, ref_key: str) -> ReadingSession:
        session = ReadingSession(ref_key, datetime.now().isoformat())
        return session

    def finish_reading(self, session: ReadingSession, pages: int, comprehension: int):
        session.end_time = datetime.now().isoformat()
        session.pages_read = pages
        session.comprehension = comprehension
        self.sessions.append(session)

    def add_note(self, note: ReadingNote):
        if not note.id:
            note.id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        self.notes.append(note)

    def add_citation(self, source: str, target: str, context: str = ""):
        self.citations.append(CitationEdge(source, target, context))

    def get_notes_for(self, ref_key: str) -> List[ReadingNote]:
        return [n for n in self.notes if n.ref_key == ref_key]

    def get_all_notes_by_type(self, note_type: str) -> List[ReadingNote]:
        return [n for n in self.notes if n.note_type == note_type]

    def citation_graph(self) -> Dict[str, List[str]]:
        """构建引用关系图 {文献: [引用了哪些文献]}"""
        graph = defaultdict(set)
        for edge in self.citations:
            graph[edge.source].add(edge.target)
        return {k: sorted(v) for k, v in graph.items()}

    def most_cited(self, top_n: int = 10) -> List[tuple]:
        """被引用最多的文献"""
        cited_count = Counter(edge.target for edge in self.citations)
        return cited_count.most_common(top_n)

    def reading_stats(self) -> dict:
        """阅读统计"""
        if not self.sessions:
            return {"total_sessions": 0, "total_pages": 0, "total_hours": 0}

        total_pages = sum(s.pages_read for s in self.sessions)
        total_sessions = len(self.sessions)

        # 总阅读时间
        total_minutes = 0
        for s in self.sessions:
            if s.end_time:
                start = datetime.fromisoformat(s.start_time)
                end = datetime.fromisoformat(s.end_time)
                total_minutes += (end - start).total_seconds() / 60

        # 每周统计
        weekly = defaultdict(lambda: {"pages": 0, "sessions": 0})
        for s in self.sessions:
            if s.start_time:
                dt = datetime.fromisoformat(s.start_time)
                week = dt.strftime("%Y-W%U")
                weekly[week]["pages"] += s.pages_read
                weekly[week]["sessions"] += 1

        # 理解度平均
        avg_comprehension = round(
            sum(s.comprehension for s in self.sessions) / total_sessions, 1
        ) if total_sessions else 0

        return {
            "total_sessions": total_sessions,
            "total_pages": total_pages,
            "total_hours": round(total_minutes / 60, 1),
            "avg_comprehension": avg_comprehension,
            "avg_speed_ppm": round(total_pages / max(total_minutes, 1), 2),  # 页/分钟
            "weekly": dict(weekly),
            "notes_total": len(self.notes),
            "streak_days": self._calc_streak(),
        }

    def _calc_streak(self) -> int:
        """连续阅读天数"""
        days = set()
        for s in self.sessions:
            if s.start_time:
                days.add(datetime.fromisoformat(s.start_time).strftime("%Y-%m-%d"))

        sorted_days = sorted(days, reverse=True)
        if not sorted_days:
            return 0

        streak = 1
        for i in range(len(sorted_days) - 1):
            d1 = datetime.strptime(sorted_days[i], "%Y-%m-%d")
            d2 = datetime.strptime(sorted_days[i + 1], "%Y-%m-%d")
            if (d1 - d2).days == 1:
                streak += 1
            else:
                break
        return streak

    def knowledge_map(self) -> List[tuple]:
        """基于笔记标签的知识关联"""
        co_occurrence = Counter()
        for note in self.notes:
            for i, t1 in enumerate(note.tags):
                for t2 in note.tags[i + 1:]:
                    co_occurrence[(t1, t2)] += 1
        return co_occurrence.most_common(20)

    def report(self):
        print("=" * 55)
        print("📖 文献阅读追踪报告")
        print("=" * 55)

        stats = self.reading_stats()
        print(f"\n📊 阅读统计:")
        print(f"   阅读次数: {stats['total_sessions']}")
        print(f"   总页数: {stats['total_pages']}")
        print(f"   总时长: {stats['total_hours']} 小时")
        print(f"   平均速度: {stats['avg_speed_ppm']} 页/分钟")
        print(f"   理解度: {'⭐' * stats['avg_comprehension']}")
        print(f"   笔记数: {stats['notes_total']}")
        print(f"   🔥 连续阅读: {stats['streak_days']} 天")

        if stats.get("weekly"):
            print(f"\n📅 每周记录:")
            for week, data in sorted(stats['weekly'].items())[-4:]:
                bar = "█" * min(data['pages'] // 5, 25)
                print(f"   {week}: {bar} {data['pages']}页 ({data['sessions']}次)")


def main():
    print("=" * 55)
    print("📖 文献阅读追踪 + 笔记系统")
    print("=" * 55)

    tracker = ReadingTracker()

    # 模拟阅读数据
    refs = ["smith2024mars", "wang2023vtvl", "liu2025rl", "kim2024cnn"]
    for i in range(12):
        session = tracker.start_reading(random.choice(refs))
        tracker.finish_reading(session, random.randint(5, 30), random.randint(3, 5))

    # 添加笔记
    tracker.add_note(ReadingNote("smith2024mars", "3.2 PID参数整定",
        "作者提出的自适应调节方法很巧妙，可以考虑在我们的系统中加入类似机制",
        "idea", "p45", ["PID", "自适应控制", "参数整定"]))
    tracker.add_note(ReadingNote("wang2023vtvl", "5.1 仿真结果",
        "图5.3显示燃料消耗对控制精度的影响是非线性的，需要进一步建模",
        "question", "p78", ["燃料", "非线性", "仿真验证"]))

    # 引用关系
    tracker.add_citation("wang2023vtvl", "smith2024mars", "参考了Smith的PID参数整定方法")
    tracker.add_citation("liu2025rl", "wang2023vtvl", "基于Wang的VTVL模型做了RL改进")
    tracker.add_citation("liu2025rl", "smith2024mars", "对比了传统PID和RL方法")

    tracker.report()

    print(f"\n📎 引用网络:")
    for src, targets in tracker.citation_graph().items():
        print(f"   {src} → {', '.join(targets)}")

    print(f"\n🏆 被引最多: {tracker.most_cited(3)}")
    print(f"\n🧠 知识关联: {tracker.knowledge_map()[:5]}")
    print(f"\n✅ 阅读追踪器演示完成")


if __name__ == "__main__":
    import random
    main()
