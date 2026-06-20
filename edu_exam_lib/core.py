"""
核心数据结构定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Union
from collections import defaultdict
from enum import Enum
import uuid
import json
import csv
import io


class DifficultyLevel(Enum):
    """难度等级"""
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'

    @classmethod
    def from_str(cls, s: str) -> 'DifficultyLevel':
        mapping = {
            'easy': cls.EASY,
            '简单': cls.EASY,
            '易': cls.EASY,
            'medium': cls.MEDIUM,
            '中等': cls.MEDIUM,
            '中': cls.MEDIUM,
            'hard': cls.HARD,
            '困难': cls.HARD,
            '难': cls.HARD,
        }
        if s.lower() in mapping:
            return mapping[s.lower()]
        raise ValueError(f"未知难度等级: {s}")


class QuestionType(Enum):
    """题目类型"""
    SINGLE_CHOICE = 'single_choice'
    MULTIPLE_CHOICE = 'multiple_choice'
    TRUE_FALSE = 'true_false'

    @classmethod
    def from_str(cls, s: str) -> 'QuestionType':
        mapping = {
            'single_choice': cls.SINGLE_CHOICE,
            '单选': cls.SINGLE_CHOICE,
            '单选题': cls.SINGLE_CHOICE,
            'multiple_choice': cls.MULTIPLE_CHOICE,
            '多选': cls.MULTIPLE_CHOICE,
            '多选题': cls.MULTIPLE_CHOICE,
            'true_false': cls.TRUE_FALSE,
            '判断': cls.TRUE_FALSE,
            '判断题': cls.TRUE_FALSE,
        }
        if s.lower() in mapping:
            return mapping[s.lower()]
        raise ValueError(f"未知题目类型: {s}")


@dataclass
class Question:
    """选择题题目"""
    question_id: str
    content: str
    options: List[str]
    correct_answer: List[str]
    knowledge_points: List[str]
    difficulty: DifficultyLevel
    question_type: QuestionType = QuestionType.SINGLE_CHOICE
    score: float = 1.0
    explanation: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.question_id:
            self.question_id = str(uuid.uuid4())[:8]
        if isinstance(self.difficulty, str):
            self.difficulty = DifficultyLevel.from_str(self.difficulty)
        if isinstance(self.question_type, str):
            self.question_type = QuestionType.from_str(self.question_type)
        if isinstance(self.correct_answer, str):
            self.correct_answer = [self.correct_answer.upper()]
        else:
            self.correct_answer = [a.upper() for a in self.correct_answer]

    def is_correct(self, answer: List[str]) -> bool:
        """判断答案是否正确"""
        normalized = [a.upper() for a in answer]
        return sorted(normalized) == sorted(self.correct_answer)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'question_id': self.question_id,
            'content': self.content,
            'options': self.options,
            'correct_answer': self.correct_answer,
            'knowledge_points': self.knowledge_points,
            'difficulty': self.difficulty.value,
            'question_type': self.question_type.value,
            'score': self.score,
            'explanation': self.explanation,
            'tags': self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Question':
        return cls(**data)


@dataclass
class ExamRule:
    """组卷规则"""
    total_questions: int
    knowledge_points: Optional[Dict[str, int]] = None
    difficulty_ratio: Optional[Dict[DifficultyLevel, float]] = None
    question_type_ratio: Optional[Dict[QuestionType, float]] = None
    shuffle_options: bool = True
    shuffle_questions: bool = True
    num_versions: int = 1
    exam_title: str = "测试试卷"
    exam_duration: int = 60
    allowed_knowledge_points: Optional[List[str]] = None
    excluded_knowledge_points: Optional[List[str]] = None

    def __post_init__(self):
        if self.difficulty_ratio is None:
            self.difficulty_ratio = {
                DifficultyLevel.EASY: 0.3,
                DifficultyLevel.MEDIUM: 0.5,
                DifficultyLevel.HARD: 0.2,
            }
        elif isinstance(list(self.difficulty_ratio.keys())[0], str):
            self.difficulty_ratio = {
                DifficultyLevel.from_str(k): v
                for k, v in self.difficulty_ratio.items()
            }

        if self.question_type_ratio is None:
            self.question_type_ratio = {
                QuestionType.SINGLE_CHOICE: 0.7,
                QuestionType.MULTIPLE_CHOICE: 0.2,
                QuestionType.TRUE_FALSE: 0.1,
            }
        elif isinstance(list(self.question_type_ratio.keys())[0], str):
            self.question_type_ratio = {
                QuestionType.from_str(k): v
                for k, v in self.question_type_ratio.items()
            }

        if self.num_versions < 1:
            raise ValueError("试卷版本数不能小于1")

        if self.total_questions <= 0:
            raise ValueError("题目总数必须大于0")

    def validate(self) -> Tuple[bool, List[str]]:
        """验证规则是否合理"""
        errors = []
        if self.total_questions <= 0:
            errors.append("题目总数必须大于0")

        if self.difficulty_ratio:
            total_ratio = sum(self.difficulty_ratio.values())
            if abs(total_ratio - 1.0) > 0.01:
                errors.append(f"难度比例之和应为1，当前为{total_ratio}")

        if self.question_type_ratio:
            total_ratio = sum(self.question_type_ratio.values())
            if abs(total_ratio - 1.0) > 0.01:
                errors.append(f"题型比例之和应为1，当前为{total_ratio}")

        if self.knowledge_points:
            total = sum(self.knowledge_points.values())
            if total != self.total_questions:
                errors.append(f"知识点题目数之和({total})不等于总题数({self.total_questions})")

        return len(errors) == 0, errors


@dataclass
class ExamPaper:
    """试卷结构"""
    paper_id: str
    version: str
    title: str
    duration: int
    questions: List[Dict[str, Any]]
    option_mapping: Dict[str, Dict[str, str]]
    answer_key: Dict[str, List[str]]
    generated_at: str
    total_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'paper_id': self.paper_id,
            'version': self.version,
            'title': self.title,
            'duration': self.duration,
            'questions': self.questions,
            'option_mapping': self.option_mapping,
            'answer_key': self.answer_key,
            'generated_at': self.generated_at,
            'total_score': self.total_score,
        }


@dataclass
class StudentAnswer:
    """学生答案"""
    student_id: str
    student_name: str
    paper_id: str
    answers: Union[Dict[str, Any], List[Dict[str, Any]]]
    submitted_at: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.answers, list):
            self.raw_answers = self.answers.copy()
        else:
            self.raw_answers = None

        if isinstance(self.answers, list):
            seen = {}
            for entry in self.answers:
                qid = entry.get('question_id') or entry.get('qid')
                if qid:
                    if qid in seen:
                        seen[qid] += 1
                    else:
                        seen[qid] = 1
            self._duplicate_question_ids = [qid for qid, count in seen.items() if count > 1]
            self._question_id_counts = seen

            normalized = {}
            for entry in self.answers:
                qid = entry.get('question_id') or entry.get('qid')
                ans = entry.get('answer') or entry.get('answers') or entry.get('ans')
                if qid:
                    if isinstance(ans, str):
                        normalized[qid] = [ans.upper()]
                    elif ans is not None:
                        normalized[qid] = [a.upper() for a in ans]
                    else:
                        normalized[qid] = []
            self.answers = normalized
        else:
            self._duplicate_question_ids = []
            normalized = {}
            for qid, ans in self.answers.items():
                if isinstance(ans, str):
                    normalized[qid] = [ans.upper()]
                else:
                    normalized[qid] = [a.upper() for a in ans]
            self.answers = normalized

    @property
    def has_duplicates(self) -> bool:
        """是否有重复题号"""
        return len(self._duplicate_question_ids) > 0

    @property
    def duplicate_question_ids(self) -> List[str]:
        """重复的题号列表"""
        return self._duplicate_question_ids

    def validate(self, exam_paper: ExamPaper) -> Tuple[bool, List[str], List[str]]:
        """验证答案与试卷是否匹配

        Returns:
            (是否有效, 错误列表, 缺失题号列表)
        """
        errors = []
        question_ids = {q['question_id'] for q in exam_paper.questions}

        if self.has_duplicates:
            if hasattr(self, '_question_id_counts'):
                dup_detail = ", ".join(
                    f"{qid}(出现{self._question_id_counts[qid]}次)" 
                    for qid in self._duplicate_question_ids
                )
            else:
                dup_detail = ", ".join(
                    f"{qid}(出现多次)" 
                    for qid in self._duplicate_question_ids
                )
            errors.append(f"存在重复题号: {dup_detail}")

        for qid in self.answers:
            if qid not in question_ids:
                errors.append(f"题号 {qid} 不在试卷中")

        answered_ids = set(self.answers.keys())
        missing = sorted(question_ids - answered_ids)

        return len(errors) == 0, errors, missing


@dataclass
class QuestionResult:
    """单题判分结果"""
    question_id: str
    student_answer: List[str]
    correct_answer: List[str]
    is_correct: bool
    score: float
    max_score: float
    knowledge_points: List[str]
    difficulty: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'question_id': self.question_id,
            'student_answer': self.student_answer,
            'correct_answer': self.correct_answer,
            'is_correct': self.is_correct,
            'score': self.score,
            'max_score': self.max_score,
            'knowledge_points': self.knowledge_points,
            'difficulty': self.difficulty,
        }


@dataclass
class ExamResult:
    """考试结果"""
    student_id: str
    student_name: str
    paper_id: str
    total_score: float
    max_score: float
    percentage: float
    question_results: List[QuestionResult]
    knowledge_mastery: Dict[str, Dict[str, float]]
    error_reasons: List[Dict[str, Any]]
    graded_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'student_id': self.student_id,
            'student_name': self.student_name,
            'paper_id': self.paper_id,
            'total_score': self.total_score,
            'max_score': self.max_score,
            'percentage': self.percentage,
            'question_results': [qr.to_dict() for qr in self.question_results],
            'knowledge_mastery': self.knowledge_mastery,
            'error_reasons': self.error_reasons,
            'graded_at': self.graded_at,
        }


@dataclass
class MergeResult:
    """多场考试合并结果"""
    merged_results: List[ExamResult]
    duplicates: List[Dict[str, Any]]
    missing_answers: List[Dict[str, Any]]
    errors: List[str]
    exam_info: List[Dict[str, Any]] = field(default_factory=list)
    student_summary: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'merged_results': [r.to_dict() for r in self.merged_results],
            'duplicates': self.duplicates,
            'missing_answers': self.missing_answers,
            'errors': self.errors,
            'exam_info': self.exam_info,
            'student_summary': self.student_summary,
        }

    def get_student_summary(self, student_id: str) -> Optional[Dict[str, Any]]:
        """获取指定学生的汇总信息"""
        return self.student_summary.get(student_id)

    def get_all_students_summary(self) -> List[Dict[str, Any]]:
        """获取所有学生的汇总信息列表"""
        return sorted(self.student_summary.values(), key=lambda x: x['total_score'], reverse=True)

    def get_knowledge_trend(self, student_id: str) -> Optional[Dict[str, Any]]:
        """获取指定学生的知识点掌握变化趋势

        Args:
            student_id: 学生ID

        Returns:
            包含各知识点各场次掌握度、变化趋势、是否薄弱等信息的字典
        """
        if student_id not in self.student_summary:
            return None

        student_results = [r for r in self.merged_results if r.student_id == student_id]
        student_results.sort(key=lambda x: x.paper_id)

        kp_exam_scores = defaultdict(list)

        for exam_idx, result in enumerate(student_results, 1):
            for kp, mastery in result.knowledge_mastery.items():
                kp_exam_scores[kp].append({
                    'exam_index': exam_idx,
                    'paper_id': result.paper_id,
                    'mastery': mastery.get('mastery_ratio', 0),
                    'correct_count': mastery.get('correct_count', 0),
                    'total_count': mastery.get('total_count', 0),
                })

        kp_trend = {}
        for kp, scores in kp_exam_scores.items():
            mastery_values = [s['mastery'] for s in scores]
            if len(mastery_values) >= 2:
                diff = mastery_values[-1] - mastery_values[0]
                if diff > 0.1:
                    trend = '上升'
                elif diff < -0.1:
                    trend = '下降'
                else:
                    trend = '平稳'
            else:
                trend = '数据不足'

            weak_threshold = 0.6
            is_weak = all(m < weak_threshold for m in mastery_values)
            is_consistently_strong = all(m >= 0.8 for m in mastery_values)

            kp_trend[kp] = {
                'knowledge_point': kp,
                'exam_count': len(scores),
                'mastery_history': scores,
                'avg_mastery': sum(mastery_values) / len(mastery_values) if mastery_values else 0,
                'first_mastery': mastery_values[0] if mastery_values else 0,
                'last_mastery': mastery_values[-1] if mastery_values else 0,
                'trend': trend,
                'is_weak': is_weak,
                'is_consistently_strong': is_consistently_strong,
            }

        weak_kps = sorted(
            [kp for kp, info in kp_trend.items() if info['is_weak']],
            key=lambda kp: kp_trend[kp]['avg_mastery']
        )
        improving_kps = sorted(
            [kp for kp, info in kp_trend.items() if info['trend'] == '上升'],
            key=lambda kp: kp_trend[kp]['last_mastery'] - kp_trend[kp]['first_mastery'],
            reverse=True
        )
        declining_kps = sorted(
            [kp for kp, info in kp_trend.items() if info['trend'] == '下降'],
            key=lambda kp: kp_trend[kp]['first_mastery'] - kp_trend[kp]['last_mastery'],
            reverse=True
        )

        return {
            'student_id': student_id,
            'student_name': self.student_summary[student_id]['student_name'],
            'knowledge_points': kp_trend,
            'weak_points': weak_kps,
            'improving_points': improving_kps,
            'declining_points': declining_kps,
        }

    def get_class_knowledge_trend(self) -> Dict[str, Any]:
        """获取全班知识点掌握变化趋势

        Returns:
            全班各知识点的平均掌握度变化、薄弱知识点等
        """
        all_kps = set()
        exam_kp_avg = defaultdict(lambda: defaultdict(list))

        for result in self.merged_results:
            exam_idx = self._get_exam_index(result.paper_id)
            for kp, mastery in result.knowledge_mastery.items():
                all_kps.add(kp)
                exam_kp_avg[exam_idx][kp].append(mastery.get('mastery_ratio', 0))

        kp_class_trend = {}
        for kp in all_kps:
            exam_avg = {}
            for exam_idx in range(1, len(self.exam_info) + 1):
                scores = exam_kp_avg[exam_idx].get(kp, [])
                if scores:
                    exam_avg[exam_idx] = sum(scores) / len(scores)

            avg_values = list(exam_avg.values())
            if len(avg_values) >= 2:
                diff = avg_values[-1] - avg_values[0]
                if diff > 0.05:
                    trend = '上升'
                elif diff < -0.05:
                    trend = '下降'
                else:
                    trend = '平稳'
            else:
                trend = '数据不足'

            weak_count = 0
            for result in self.merged_results:
                if kp in result.knowledge_mastery:
                    if result.knowledge_mastery[kp].get('mastery_ratio', 0) < 0.6:
                        weak_count += 1

            kp_class_trend[kp] = {
                'knowledge_point': kp,
                'exam_avg': exam_avg,
                'avg_mastery': sum(avg_values) / len(avg_values) if avg_values else 0,
                'trend': trend,
                'weak_student_count': weak_count,
                'total_students': len(self.student_summary),
                'weak_rate': weak_count / len(self.student_summary) if self.student_summary else 0,
            }

        weak_kps = sorted(
            [kp for kp, info in kp_class_trend.items() if info['weak_rate'] > 0.4],
            key=lambda kp: kp_class_trend[kp]['weak_rate'],
            reverse=True
        )

        return {
            'knowledge_points': kp_class_trend,
            'weak_points': weak_kps,
            'total_knowledge_points': len(all_kps),
        }

    def generate_knowledge_trend_report(self, student_id: Optional[str] = None) -> str:
        """生成知识点掌握变化趋势报告

        Args:
            student_id: 学生ID，不传则生成全班报告

        Returns:
            报告文本
        """
        if student_id:
            trend = self.get_knowledge_trend(student_id)
            if not trend:
                return f"未找到学生 {student_id} 的数据"

            lines = []
            lines.append("=" * 70)
            lines.append(f"知识点掌握变化报告 - {trend['student_name']}({student_id})")
            lines.append("=" * 70)
            lines.append("")

            lines.append("-" * 70)
            lines.append("各知识点掌握情况")
            lines.append("-" * 70)

            sorted_kps = sorted(
                trend['knowledge_points'].keys(),
                key=lambda kp: trend['knowledge_points'][kp]['avg_mastery'],
                reverse=True
            )

            for kp in sorted_kps:
                info = trend['knowledge_points'][kp]
                tag = ""
                if info['is_weak']:
                    tag = " ⚠️连续薄弱"
                elif info['is_consistently_strong']:
                    tag = " ✅持续优秀"
                elif info['trend'] == '上升':
                    tag = " 📈上升"
                elif info['trend'] == '下降':
                    tag = " 📉下降"

                lines.append(f"\n【{kp}】{tag}")
                lines.append(f"  平均掌握度: {info['avg_mastery']*100:.1f}%  "
                            f"趋势: {info['trend']}")
                lines.append(f"  变化: 首{info['first_mastery']*100:.1f}% "
                            f"→ 末{info['last_mastery']*100:.1f}%")
                lines.append(f"  各场次:")
                for s in info['mastery_history']:
                    lines.append(f"    场次{s['exam_index']}: {s['mastery']*100:.1f}% "
                                f"({s['correct_count']}/{s['total_count']}题)")

            if trend['weak_points']:
                lines.append("\n" + "-" * 70)
                lines.append("⚠️  连续薄弱知识点（所有场次均低于60%）:")
                lines.append("-" * 70)
                for kp in trend['weak_points']:
                    info = trend['knowledge_points'][kp]
                    lines.append(f"  • {kp} (平均{info['avg_mastery']*100:.1f}%)")

            if trend['improving_points']:
                lines.append("\n" + "-" * 70)
                lines.append("📈 进步知识点（掌握度提升10%以上）:")
                lines.append("-" * 70)
                for kp in trend['improving_points'][:5]:
                    info = trend['knowledge_points'][kp]
                    diff = info['last_mastery'] - info['first_mastery']
                    lines.append(f"  • {kp} (提升{diff*100:+.1f}%)")

            if trend['declining_points']:
                lines.append("\n" + "-" * 70)
                lines.append("📉 退步知识点（掌握度下降10%以上）:")
                lines.append("-" * 70)
                for kp in trend['declining_points'][:5]:
                    info = trend['knowledge_points'][kp]
                    diff = info['last_mastery'] - info['first_mastery']
                    lines.append(f"  • {kp} (下降{diff*100:+.1f}%)")

            lines.append("\n" + "=" * 70)
            return "\n".join(lines)
        else:
            trend = self.get_class_knowledge_trend()
            lines = []
            lines.append("=" * 70)
            lines.append("全班知识点掌握变化报告")
            lines.append("=" * 70)
            lines.append("")
            lines.append(f"学生总数: {len(self.student_summary)} 人")
            lines.append(f"知识点数量: {trend['total_knowledge_points']} 个")
            lines.append("")

            lines.append("-" * 70)
            lines.append("各知识点班级平均掌握度")
            lines.append("-" * 70)

            sorted_kps = sorted(
                trend['knowledge_points'].keys(),
                key=lambda kp: trend['knowledge_points'][kp]['avg_mastery'],
                reverse=True
            )

            for kp in sorted_kps:
                info = trend['knowledge_points'][kp]
                weak_pct = info['weak_rate'] * 100
                tag = ""
                if info['weak_rate'] > 0.5:
                    tag = " ⚠️全班薄弱"
                elif info['trend'] == '上升':
                    tag = " 📈上升"
                elif info['trend'] == '下降':
                    tag = " 📉下降"

                lines.append(f"\n【{kp}】{tag}")
                lines.append(f"  平均掌握度: {info['avg_mastery']*100:.1f}%  "
                            f"趋势: {info['trend']}")
                lines.append(f"  薄弱人数: {info['weak_student_count']}/{info['total_students']} "
                            f"({weak_pct:.1f}%)")
                lines.append(f"  各场次平均:")
                for exam_idx in sorted(info['exam_avg'].keys()):
                    lines.append(f"    场次{exam_idx}: {info['exam_avg'][exam_idx]*100:.1f}%")

            if trend['weak_points']:
                lines.append("\n" + "-" * 70)
                lines.append("⚠️  全班薄弱知识点（薄弱率>40%）:")
                lines.append("-" * 70)
                for kp in trend['weak_points']:
                    info = trend['knowledge_points'][kp]
                    lines.append(f"  • {kp} (薄弱率{info['weak_rate']*100:.1f}%, "
                                f"平均{info['avg_mastery']*100:.1f}%)")

            lines.append("\n" + "=" * 70)
            return "\n".join(lines)

    def export_to_json(self, file_path: Optional[str] = None) -> str:
        """导出合并结果为JSON格式

        包含：各场成绩、缺考场次、重复提交记录、汇总排名

        Args:
            file_path: 输出文件路径，不传则返回JSON字符串

        Returns:
            JSON字符串或文件路径
        """
        export_data = {
            'summary': {
                'total_exams': len(self.exam_info),
                'total_students': len(self.student_summary),
                'total_results': len(self.merged_results),
                'duplicate_count': len(self.duplicates),
                'error_count': len(self.errors),
            },
            'exam_info': self.exam_info,
            'duplicates': self.duplicates,
            'errors': self.errors,
            'student_summary': self.get_all_students_summary(),
            'ranking': [
                {
                    'rank': rank,
                    'student_id': s['student_id'],
                    'student_name': s['student_name'],
                    'total_score': s['total_score'],
                    'avg_score': s['avg_score'],
                    'exam_count': s['exam_count'],
                    'missing_exams': s['missing_exams'],
                    'exam_scores': s['exam_scores'],
                }
                for rank, s in enumerate(self.get_all_students_summary(), 1)
            ],
        }

        json_str = json.dumps(export_data, ensure_ascii=False, indent=2, default=str)

        if file_path:
            import os
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            return file_path

        return json_str

    def export_to_csv(self, file_path: Optional[str] = None) -> str:
        """导出合并结果为CSV格式

        包含：排名、学号、姓名、各场成绩、总分、平均分、参考场次、缺考场次、是否有重复提交

        Args:
            file_path: 输出文件路径，不传则返回CSV字符串

        Returns:
            CSV字符串或文件路径
        """
        output = io.StringIO()
        writer = csv.writer(output)

        header = ['排名', '学号', '姓名']
        for i, info in enumerate(self.exam_info, 1):
            header.append(f'场次{i}成绩')
            header.append(f'场次{i}满分')
            header.append(f'场次{i}得分率%')
        header.extend(['总分', '平均分', '参考场次', '缺考场次', '是否有重复提交', '重复次数'])
        writer.writerow(header)

        student_dup_count = defaultdict(int)
        for dup in self.duplicates:
            student_dup_count[dup['student_id']] += 1

        for rank, s in enumerate(self.get_all_students_summary(), 1):
            row = [rank, s['student_id'], s['student_name']]
            for exam_score in s['exam_scores']:
                if exam_score['has_score']:
                    row.append(exam_score['score'])
                    row.append(exam_score['max_score'])
                    row.append(exam_score['percentage'])
                else:
                    row.append('缺考')
                    row.append(exam_score['max_score'])
                    row.append(0)
            row.extend([
                s['total_score'],
                s['avg_score'],
                s['exam_count'],
                ','.join([str(x) for x in s['missing_exams']]) if s['missing_exams'] else '',
                '是' if student_dup_count.get(s['student_id'], 0) > 0 else '否',
                student_dup_count.get(s['student_id'], 0),
            ])
            writer.writerow(row)

        csv_str = output.getvalue()

        if file_path:
            import os
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
            with open(file_path, 'w', encoding='utf-8-sig') as f:
                f.write(csv_str)
            return file_path

        return csv_str

    def _get_exam_index(self, paper_id: str) -> int:
        """根据试卷ID获取场次索引"""
        for i, info in enumerate(self.exam_info, 1):
            if info['paper_id'] == paper_id:
                return i
        return 0

    def generate_summary_report(self) -> str:
        """生成合并汇总报告"""
        lines = []
        lines.append("=" * 70)
        lines.append("多场考试合并汇总报告")
        lines.append("=" * 70)

        lines.append(f"\n合并场次: {len(self.exam_info)} 场")
        for i, info in enumerate(self.exam_info, 1):
            lines.append(f"  场次{i}: 试卷{info['paper_id']} ({info['student_count']}人, 满分{info['max_score']}分)")

        lines.append(f"\n总学生数: {len(self.student_summary)} 人")
        lines.append(f"合并后总记录: {len(self.merged_results)} 条")

        if self.duplicates:
            lines.append(f"\n⚠️  重复记录: {len(self.duplicates)} 条")
            for dup in self.duplicates:
                lines.append(f"  - {dup['student_name']}({dup['student_id']}) "
                           f"试卷{dup['paper_id']} 场次{dup['exam_index']} 得分{dup['score']}")

        if self.errors:
            lines.append(f"\n❌ 错误信息: {len(self.errors)} 条")
            for err in self.errors:
                lines.append(f"  - {err}")

        lines.append("\n" + "-" * 70)
        lines.append("学生成绩汇总 (按总分排序)")
        lines.append("-" * 70)
        lines.append(f"{'排名':<4}{'学号':<10}{'姓名':<10}{'总分':<8}{'平均分':<8}"
                    f"{'参考场次':<10}{'缺考场次':<10}")
        lines.append("-" * 70)

        for rank, summary in enumerate(self.get_all_students_summary(), 1):
            missing_exams = summary.get('missing_exams', [])
            missing_str = ",".join([str(x) for x in missing_exams]) if missing_exams else "-"
            lines.append(f"{rank:<4}{summary['student_id']:<10}{summary['student_name']:<10}"
                        f"{summary['total_score']:<8.1f}{summary['avg_score']:<8.1f}"
                        f"{summary['exam_count']:<10}{missing_str:<10}")

            for exam_info in summary['exam_scores']:
                status = "✅" if exam_info.get('has_score', True) else "❌缺考"
                lines.append(f"     场次{exam_info['exam_index']}: "
                            f"{exam_info.get('score', '缺考')}/{exam_info.get('max_score', '-')} "
                            f"({exam_info.get('percentage', '-')}%) {status}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)
