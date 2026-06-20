"""
统计分析模块
"""

from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
from .core import ExamResult, QuestionResult


class ExamStatistics:
    """考试统计分析类"""

    def __init__(self, results: List[ExamResult]):
        self.results = results
        self._validate_results()

    def _validate_results(self):
        """验证结果数据"""
        if not self.results:
            raise ValueError("没有考试结果数据")

        paper_ids = {r.paper_id for r in self.results}
        if len(paper_ids) > 1:
            raise ValueError(
                f"统计分析要求使用同一份试卷的结果，检测到 {len(paper_ids)} 份不同试卷"
            )

    def get_score_distribution(self,
                                bins: Optional[List[Tuple[float, float, str]]] = None
                                ) -> Dict[str, Dict[str, Any]]:
        """成绩分段统计"""
        if bins is None:
            bins = [
                (90, 101, '优秀 (90-100)'),
                (80, 90, '良好 (80-89)'),
                (70, 80, '中等 (70-79)'),
                (60, 70, '及格 (60-69)'),
                (0, 60, '不及格 (0-59)'),
            ]

        distribution: Dict[str, Dict[str, Any]] = {}
        for low, high, label in bins:
            count = sum(1 for r in self.results
                        if low <= r.percentage < high)
            distribution[label] = {
                'count': count,
                'percentage': round(count / len(self.results) * 100, 2),
                'range': (low, high),
                'students': [(r.student_id, r.student_name, r.percentage)
                             for r in self.results
                             if low <= r.percentage < high]
            }

        return distribution

    def get_descriptive_stats(self) -> Dict[str, float]:
        """描述性统计"""
        percentages = [r.percentage for r in self.results]
        total_scores = [r.total_score for r in self.results]

        percentages.sort()
        n = len(percentages)

        median = percentages[n // 2] if n % 2 == 1 else \
            (percentages[n // 2 - 1] + percentages[n // 2]) / 2

        mean = sum(percentages) / n
        variance = sum((x - mean) ** 2 for x in percentages) / n
        std_dev = variance ** 0.5

        return {
            'count': n,
            'mean': round(mean, 2),
            'median': round(median, 2),
            'std_dev': round(std_dev, 2),
            'min': round(min(percentages), 2),
            'max': round(max(percentages), 2),
            'range': round(max(percentages) - min(percentages), 2),
            'total_score_mean': round(sum(total_scores) / n, 2),
            'pass_count': sum(1 for p in percentages if p >= 60),
            'pass_rate': round(sum(1 for p in percentages if p >= 60) / n * 100, 2),
            'excellent_count': sum(1 for p in percentages if p >= 90),
            'excellent_rate': round(sum(1 for p in percentages if p >= 90) / n * 100, 2),
        }

    def get_knowledge_point_stats(self) -> Dict[str, Dict[str, Any]]:
        """全班知识点掌握情况统计"""
        kp_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {'correct': 0, 'total': 0, 'score': 0, 'max_score': 0}
        )

        for result in self.results:
            for kp, mastery in result.knowledge_mastery.items():
                kp_stats[kp]['correct'] += mastery['correct_count']
                kp_stats[kp]['total'] += mastery['total_count']
                kp_stats[kp]['score'] += mastery['score']
                kp_stats[kp]['max_score'] += mastery['max_score']

        result: Dict[str, Dict[str, Any]] = {}
        for kp, stats in kp_stats.items():
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            score_rate = (stats['score'] / stats['max_score'] * 100) if stats['max_score'] > 0 else 0
            result[kp] = {
                'accuracy': round(accuracy, 2),
                'score_rate': round(score_rate, 2),
                'correct_count': stats['correct'],
                'total_count': stats['total'],
                'total_score': stats['score'],
                'max_total_score': stats['max_score'],
            }

        return result

    def get_question_stats(self) -> Dict[str, Dict[str, Any]]:
        """各题目正确率统计"""
        q_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'correct': 0, 'total': 0, 'score': 0, 'max_score': 0}
        )

        question_info: Dict[str, Dict[str, Any]] = {}

        for result in self.results:
            for qr in result.question_results:
                qid = qr.question_id
                q_stats[qid]['total'] += 1
                q_stats[qid]['max_score'] += qr.max_score
                if qid not in question_info:
                    question_info[qid] = {
                        'knowledge_points': qr.knowledge_points,
                        'difficulty': qr.difficulty,
                        'max_score_per_question': qr.max_score,
                    }
                if qr.is_correct:
                    q_stats[qid]['correct'] += 1
                    q_stats[qid]['score'] += qr.score

        result: Dict[str, Dict[str, Any]] = {}
        for qid, stats in q_stats.items():
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            score_rate = (stats['score'] / stats['max_score'] * 100) if stats['max_score'] > 0 else 0
            info = question_info.get(qid, {})
            result[qid] = {
                'accuracy': round(accuracy, 2),
                'score_rate': round(score_rate, 2),
                'correct_count': stats['correct'],
                'total_count': stats['total'],
                'total_score': stats['score'],
                'max_total_score': stats['max_score'],
                'difficulty': info.get('difficulty', 'unknown'),
                'knowledge_points': info.get('knowledge_points', []),
                'max_score_per_question': info.get('max_score_per_question', 0),
            }

        return result

    def get_error_reason_stats(self) -> Dict[str, Dict[str, Any]]:
        """错误原因统计"""
        reason_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'count': 0, 'lost_score': 0, 'questions': set()}
        )

        for result in self.results:
            for err in result.error_reasons:
                reason = err['reason']
                reason_stats[reason]['count'] += 1
                reason_stats[reason]['lost_score'] += err['lost_score']
                reason_stats[reason]['questions'].add(err['question_id'])

        total_errors = sum(s['count'] for s in reason_stats.values())
        result: Dict[str, Dict[str, Any]] = {}
        for reason, stats in reason_stats.items():
            result[reason] = {
                'count': stats['count'],
                'percentage': round(stats['count'] / total_errors * 100, 2) if total_errors > 0 else 0,
                'lost_score': round(stats['lost_score'], 2),
                'affected_questions': len(stats['questions']),
            }

        return result

    def get_difficulty_stats(self) -> Dict[str, Dict[str, Any]]:
        """按难度统计正确率"""
        diff_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {'correct': 0, 'total': 0, 'score': 0, 'max_score': 0}
        )

        for result in self.results:
            for qr in result.question_results:
                diff = qr.difficulty
                diff_stats[diff]['total'] += 1
                diff_stats[diff]['max_score'] += qr.max_score
                if qr.is_correct:
                    diff_stats[diff]['correct'] += 1
                    diff_stats[diff]['score'] += qr.score

        result: Dict[str, Dict[str, Any]] = {}
        for diff, stats in diff_stats.items():
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            score_rate = (stats['score'] / stats['max_score'] * 100) if stats['max_score'] > 0 else 0
            result[diff] = {
                'accuracy': round(accuracy, 2),
                'score_rate': round(score_rate, 2),
                'correct_count': stats['correct'],
                'total_count': stats['total'],
            }

        return result

    def rank_students(self, by: str = 'percentage') -> List[Dict[str, Any]]:
        """学生排名"""
        sort_keys = {
            'percentage': lambda x: x.percentage,
            'total_score': lambda x: x.total_score,
            'student_id': lambda x: x.student_id,
        }

        if by not in sort_keys:
            raise ValueError(f"不支持的排序方式: {by}")

        sorted_results = sorted(
            self.results,
            key=sort_keys[by],
            reverse=True
        )

        ranks = []
        prev_score = None
        prev_rank = 0

        for idx, result in enumerate(sorted_results, 1):
            current_score = getattr(result, by)
            if current_score != prev_score:
                rank = idx
                prev_rank = rank
                prev_score = current_score
            else:
                rank = prev_rank

            ranks.append({
                'rank': rank,
                'student_id': result.student_id,
                'student_name': result.student_name,
                'percentage': result.percentage,
                'total_score': result.total_score,
                'max_score': result.max_score,
            })

        return ranks

    def generate_statistics_report(self) -> str:
        """生成统计报告文本"""
        lines = []
        lines.append("=" * 80)
        lines.append(" " * 30 + "班级考试统计分析报告")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"试卷ID: {self.results[0].paper_id}")
        lines.append(f"统计时间: 本次分析共 {len(self.results)} 名学生")
        lines.append("")
        lines.append("-" * 80)
        lines.append("")
        lines.append("一、整体成绩描述性统计")
        lines.append("")

        stats = self.get_descriptive_stats()
        lines.append(f"  参考人数: {stats['count']} 人")
        lines.append(f"  平均分: {stats['mean']:.1f}%  (满分100%)")
        lines.append(f"  中位数: {stats['median']:.1f}%")
        lines.append(f"  标准差: {stats['std_dev']:.1f}")
        lines.append(f"  最高分: {stats['max']:.1f}%    最低分: {stats['min']:.1f}%")
        lines.append(f"  极差: {stats['range']:.1f}%")
        lines.append(f"  及格人数: {stats['pass_count']} 人  及格率: {stats['pass_rate']:.1f}%")
        lines.append(f"  优秀人数: {stats['excellent_count']} 人  优秀率: {stats['excellent_rate']:.1f}%")

        lines.append("")
        lines.append("-" * 80)
        lines.append("")
        lines.append("二、成绩分段统计")
        lines.append("")

        score_dist = self.get_score_distribution()
        for label in ['优秀 (90-100)', '良好 (80-89)', '中等 (70-79)',
                      '及格 (60-69)', '不及格 (0-59)']:
            if label in score_dist:
                d = score_dist[label]
                bar_len = int(d['percentage'] / 5)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                lines.append(
                    f"  {label:<18} {bar}  {d['count']:>3}人  {d['percentage']:>5.1f}%"
                )

        lines.append("")
        lines.append("-" * 80)
        lines.append("")
        lines.append("三、知识点掌握情况")
        lines.append("")

        kp_stats = self.get_knowledge_point_stats()
        sorted_kp = sorted(kp_stats.items(), key=lambda x: x[1]['accuracy'], reverse=True)
        for kp, s in sorted_kp:
            bar_len = int(s['accuracy'] / 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            lines.append(
                f"  {kp:<20} {bar}  {s['accuracy']:>5.1f}%  "
                f"({s['correct_count']}/{s['total_count']}题)"
            )

        lines.append("")
        lines.append("-" * 80)
        lines.append("")
        lines.append("四、各题目正确率")
        lines.append("")

        q_stats = self.get_question_stats()
        sorted_q = sorted(q_stats.items(),
                          key=lambda x: (x[1]['accuracy'], x[0]))
        for qid, s in sorted_q:
            kp = ", ".join(s['knowledge_points'])
            diff = s['difficulty']
            bar_len = int(s['accuracy'] / 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            lines.append(
                f"  题{qid:<6} {diff:<6} {bar}  {s['accuracy']:>5.1f}%  "
                f"({s['correct_count']}/{s['total_count']})  {kp}"
            )

        lines.append("")
        lines.append("-" * 80)
        lines.append("")
        lines.append("五、错误原因统计")
        lines.append("")

        err_stats = self.get_error_reason_stats()
        sorted_err = sorted(err_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        for reason, s in sorted_err:
            bar_len = int(s['percentage'] / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(
                f"  {reason:<16} {bar}  {s['count']:>3}次  "
                f"{s['percentage']:>5.1f}%  失分: {s['lost_score']:.1f}分"
            )

        lines.append("")
        lines.append("-" * 80)
        lines.append("")
        lines.append("六、学生排名 (前10名)")
        lines.append("")

        ranks = self.rank_students()
        for r in ranks[:10]:
            lines.append(
                f"  第{r['rank']:>2}名  {r['student_name']:<10} "
                f"{r['student_id']:<10}  {r['percentage']:>5.1f}%  "
                f"{r['total_score']:.1f}/{r['max_score']:.1f}分"
            )

        if len(ranks) > 10:
            lines.append(f"  ... 共 {len(ranks)} 名学生")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def export_statistics(self, output_file: str, format: str = 'txt') -> None:
        """导出统计结果"""
        if format == 'txt':
            content = self.generate_statistics_report()
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
        elif format == 'json':
            import json
            data = {
                'descriptive': self.get_descriptive_stats(),
                'score_distribution': self.get_score_distribution(),
                'knowledge_points': self.get_knowledge_point_stats(),
                'questions': self.get_question_stats(),
                'error_reasons': self.get_error_reason_stats(),
                'ranking': self.rank_students(),
            }
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"不支持的导出格式: {format}")
