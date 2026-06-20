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
    same_questions: bool = True

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
    all_results: List[ExamResult] = field(default_factory=list)

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

    def resolve_duplicates(self, strategy: str = 'highest_score') -> 'MergeResult':
        """处理重复提交记录

        Args:
            strategy: 处理策略
                - 'highest_score': 保留最高分
                - 'earliest': 保留最早提交的
                - 'manual': 标记人工处理，保留所有记录但添加标记

        Returns:
            处理后的新MergeResult
        """
        from collections import defaultdict as dd

        valid_strategies = {'highest_score', 'earliest', 'manual'}
        if strategy not in valid_strategies:
            raise ValueError(
                f"未知的重复处理策略: {strategy}。"
                f"可选策略: {', '.join(sorted(valid_strategies))}"
            )

        if not self.duplicates:
            return MergeResult(
                merged_results=list(self.merged_results),
                duplicates=list(self.duplicates),
                missing_answers=list(self.missing_answers),
                errors=list(self.errors),
                exam_info=[dict(x) for x in self.exam_info],
                student_summary={k: dict(v) for k, v in self.student_summary.items()},
                all_results=list(self.all_results),
            )

        results_by_key = dd(list)
        for r in self.all_results:
            key = (r.student_id, r.paper_id)
            exam_idx = 0
            for i, info in enumerate(self.exam_info, 1):
                if info['paper_id'] == r.paper_id:
                    exam_idx = i
                    break
            results_by_key[key].append({
                'result': r,
                'exam_index': exam_idx,
            })

        kept_results = []
        resolved_duplicates = []
        resolved_errors = []

        for (student_id, paper_id), entries in results_by_key.items():
            if len(entries) <= 1:
                kept_results.append(entries[0]['result'])
                continue

            if strategy == 'highest_score':
                best_entry = max(entries, key=lambda x: x['result'].total_score)
                best = best_entry['result']
                kept_results.append(best)

                for entry in entries:
                    is_kept = entry['result'] is best
                    resolved_duplicates.append({
                        'student_id': student_id,
                        'student_name': entry['result'].student_name,
                        'paper_id': paper_id,
                        'exam_index': entry['exam_index'],
                        'score': entry['result'].total_score,
                        'kept': is_kept,
                        'reason': '最高分' if is_kept else '重复-被覆盖(更低分)',
                    })

            elif strategy == 'earliest':
                best = entries[0]['result']
                kept_results.append(best)

                for i, entry in enumerate(entries):
                    is_kept = i == 0
                    resolved_duplicates.append({
                        'student_id': student_id,
                        'student_name': entry['result'].student_name,
                        'paper_id': paper_id,
                        'exam_index': entry['exam_index'],
                        'score': entry['result'].total_score,
                        'kept': is_kept,
                        'reason': '最早提交' if is_kept else '重复-被覆盖(非最早)',
                    })

            elif strategy == 'manual':
                for entry in entries:
                    kept_results.append(entry['result'])
                    resolved_duplicates.append({
                        'student_id': student_id,
                        'student_name': entry['result'].student_name,
                        'paper_id': paper_id,
                        'exam_index': entry['exam_index'],
                        'score': entry['result'].total_score,
                        'kept': True,
                        'reason': '人工处理-待确认',
                        'manual_review_needed': True,
                    })
                resolved_errors.append(
                    f"学生 {student_id}({entries[0]['result'].student_name}) "
                    f"在试卷 {paper_id} 有 {len(entries)} 条重复记录（需人工处理）"
                )

        from edu_exam_lib.grader import ExamGrader
        results_by_exam = dd(list)
        for r in kept_results:
            exam_idx = 0
            for i, info in enumerate(self.exam_info, 1):
                if info['paper_id'] == r.paper_id:
                    exam_idx = i
                    break
            results_by_exam[exam_idx].append(r)

        ordered_exams = []
        for i in range(1, len(self.exam_info) + 1):
            ordered_exams.append(results_by_exam.get(i, []))

        new_merge = ExamGrader.merge_exam_results(ordered_exams)

        new_merge.duplicates = resolved_duplicates
        new_merge.all_results = list(self.all_results)

        if strategy == 'manual':
            new_merge.errors = list(resolved_errors)
        else:
            dup_students = set(
                d['student_id'] for d in resolved_duplicates if not d.get('kept', False)
            )
            if dup_students:
                new_merge.errors = [
                    f"已处理重复记录 {len(resolved_duplicates)} 条，"
                    f"涉及 {len(dup_students)} 名学生，策略: {strategy}"
                ]
            else:
                new_merge.errors = []

        return new_merge

    def get_knowledge_trend(self, student_id: str) -> Optional[Dict[str, Any]]:
        """获取指定学生的知识点掌握变化趋势

        Args:
            student_id: 学生ID

        Returns:
            包含各知识点各场次掌握度、变化趋势、是否薄弱等信息的字典
        """
        if student_id not in self.student_summary:
            return None

        student_summary = self.student_summary[student_id]
        exam_scores = student_summary.get('exam_scores', [])

        result_by_exam = {}
        for r in self.merged_results:
            if r.student_id == student_id:
                exam_idx = self._get_exam_index(r.paper_id)
                if exam_idx > 0:
                    result_by_exam[exam_idx] = r

        all_kps = set()
        for r in result_by_exam.values():
            all_kps.update(r.knowledge_mastery.keys())

        kp_exam_scores = defaultdict(list)
        for exam_idx in range(1, len(self.exam_info) + 1):
            if exam_idx in result_by_exam:
                result = result_by_exam[exam_idx]
                for kp, mastery in result.knowledge_mastery.items():
                    acc = mastery.get('accuracy', 0)
                    mastery_ratio = acc / 100.0 if acc > 1 else acc
                    kp_exam_scores[kp].append({
                        'exam_index': exam_idx,
                        'paper_id': result.paper_id,
                        'has_score': True,
                        'mastery': mastery_ratio,
                        'correct_count': mastery.get('correct_count', 0),
                        'total_count': mastery.get('total_count', 0),
                    })
                for kp in all_kps:
                    if kp not in result.knowledge_mastery:
                        kp_exam_scores[kp].append({
                            'exam_index': exam_idx,
                            'paper_id': result.paper_id,
                            'has_score': True,
                            'mastery': 0.0,
                            'correct_count': 0,
                            'total_count': 0,
                        })
            else:
                paper_id = self.exam_info[exam_idx - 1]['paper_id'] if exam_idx <= len(self.exam_info) else ''
                for kp in all_kps:
                    kp_exam_scores[kp].append({
                        'exam_index': exam_idx,
                        'paper_id': paper_id,
                        'has_score': False,
                        'mastery': 0.0,
                        'correct_count': 0,
                        'total_count': 0,
                    })

        kp_trend = {}
        for kp in all_kps:
            scores = kp_exam_scores.get(kp, [])
            valid_scores = [s for s in scores if s['has_score']]
            mastery_values = [s['mastery'] for s in valid_scores]

            if len(mastery_values) >= 2:
                diff = mastery_values[-1] - mastery_values[0]
                if diff > 0.1:
                    trend = '上升'
                elif diff < -0.1:
                    trend = '下降'
                else:
                    trend = '平稳'
                last_change = mastery_values[-1] - mastery_values[-2] if len(mastery_values) >= 2 else 0
            elif len(mastery_values) == 1:
                trend = '数据不足'
                last_change = mastery_values[0]
            else:
                trend = '数据不足'
                last_change = 0

            weak_threshold = 0.6
            is_weak = len(mastery_values) > 0 and all(m < weak_threshold for m in mastery_values)
            is_consistently_strong = len(mastery_values) > 0 and all(m >= 0.8 for m in mastery_values)

            consecutive_weak_count = 0
            current_streak = 0
            for s in reversed(valid_scores):
                if s['mastery'] < weak_threshold:
                    current_streak += 1
                    consecutive_weak_count = max(consecutive_weak_count, current_streak)
                else:
                    break

            kp_trend[kp] = {
                'knowledge_point': kp,
                'exam_count': len(valid_scores),
                'total_exams': len(self.exam_info),
                'mastery_history': scores,
                'valid_mastery_values': mastery_values,
                'avg_mastery': sum(mastery_values) / len(mastery_values) if mastery_values else 0,
                'first_mastery': mastery_values[0] if mastery_values else 0,
                'last_mastery': mastery_values[-1] if mastery_values else 0,
                'last_change': last_change,
                'trend': trend,
                'is_weak': is_weak,
                'is_consistently_strong': is_consistently_strong,
                'consecutive_weak_count': consecutive_weak_count,
                'missing_exams': [s['exam_index'] for s in scores if not s['has_score']],
            }

        weak_kps = sorted(
            [kp for kp, info in kp_trend.items() if info['is_weak']],
            key=lambda kp: kp_trend[kp]['avg_mastery']
        )
        improving_kps = sorted(
            [kp for kp, info in kp_trend.items() if info['trend'] == '上升'],
            key=lambda kp: kp_trend[kp]['last_change'],
            reverse=True
        )
        declining_kps = sorted(
            [kp for kp, info in kp_trend.items() if info['trend'] == '下降'],
            key=lambda kp: kp_trend[kp]['last_change'],
        )
        consecutive_weak_kps = sorted(
            [kp for kp, info in kp_trend.items() if info['consecutive_weak_count'] >= 2],
            key=lambda kp: kp_trend[kp]['consecutive_weak_count'],
            reverse=True
        )

        return {
            'student_id': student_id,
            'student_name': student_summary['student_name'],
            'total_exams': len(self.exam_info),
            'taken_exams': len(result_by_exam),
            'knowledge_points': kp_trend,
            'weak_points': weak_kps,
            'improving_points': improving_kps,
            'declining_points': declining_kps,
            'consecutive_weak_points': consecutive_weak_kps,
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
                acc = mastery.get('accuracy', 0)
                mastery_ratio = acc / 100.0 if acc > 1 else acc
                exam_kp_avg[exam_idx][kp].append(mastery_ratio)

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
                    acc = result.knowledge_mastery[kp].get('accuracy', 0)
                    mastery_ratio = acc / 100.0 if acc > 1 else acc
                    if mastery_ratio < 0.6:
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

    def export_to_json(self, file_path: Optional[str] = None,
                        include_knowledge_trend: bool = True) -> str:
        """导出合并结果为JSON格式

        包含：各场成绩、缺考场次、重复提交记录、汇总排名、知识点掌握趋势

        Args:
            file_path: 输出文件路径，不传则返回JSON字符串
            include_knowledge_trend: 是否包含知识点掌握趋势（学生成长档案）

        Returns:
            JSON字符串或文件路径
        """
        student_dup_info = defaultdict(lambda: {'count': 0, 'has_manual_review': False})
        for dup in self.duplicates:
            sid = dup['student_id']
            student_dup_info[sid]['count'] += 1
            if dup.get('manual_review_needed'):
                student_dup_info[sid]['has_manual_review'] = True

        ranking = []
        for rank, s in enumerate(self.get_all_students_summary(), 1):
            rank_info = {
                'rank': rank,
                'student_id': s['student_id'],
                'student_name': s['student_name'],
                'total_score': s['total_score'],
                'avg_score': s['avg_score'],
                'exam_count': s['exam_count'],
                'missing_exams': s['missing_exams'],
                'exam_scores': s['exam_scores'],
                'has_duplicate': student_dup_info[s['student_id']]['count'] > 0,
                'duplicate_count': student_dup_info[s['student_id']]['count'],
                'needs_manual_review': student_dup_info[s['student_id']]['has_manual_review'],
            }
            ranking.append(rank_info)

        export_data = {
            'summary': {
                'total_exams': len(self.exam_info),
                'total_students': len(self.student_summary),
                'total_results': len(self.merged_results),
                'duplicate_count': len(self.duplicates),
                'error_count': len(self.errors),
                'duplicate_strategy': (
                    '未处理' if any(
                        '条重复记录' in e and '已处理' not in e and '默认保留' not in e
                        for e in self.errors
                    ) else '已处理'
                ),
            },
            'exam_info': self.exam_info,
            'duplicates': self.duplicates,
            'errors': self.errors,
            'student_summary': self.get_all_students_summary(),
            'ranking': ranking,
        }

        if include_knowledge_trend:
            knowledge_trend_data = {}
            for sid in self.student_summary:
                trend = self.get_knowledge_trend(sid)
                if trend:
                    kp_summary = {}
                    for kp, info in trend['knowledge_points'].items():
                        kp_summary[kp] = {
                            'avg_mastery': round(info['avg_mastery'], 4),
                            'first_mastery': round(info['first_mastery'], 4),
                            'last_mastery': round(info['last_mastery'], 4),
                            'last_change': round(info['last_change'], 4),
                            'trend': info['trend'],
                            'is_weak': info['is_weak'],
                            'is_consistently_strong': info['is_consistently_strong'],
                            'consecutive_weak_count': info['consecutive_weak_count'],
                            'exam_count': info['exam_count'],
                            'mastery_history': [
                                {
                                    'exam_index': s['exam_index'],
                                    'has_score': s['has_score'],
                                    'mastery': round(s['mastery'], 4),
                                }
                                for s in info['mastery_history']
                            ],
                        }
                    knowledge_trend_data[sid] = {
                        'student_id': sid,
                        'student_name': trend['student_name'],
                        'total_exams': trend['total_exams'],
                        'taken_exams': trend['taken_exams'],
                        'weak_points': trend['weak_points'],
                        'improving_points': trend['improving_points'],
                        'declining_points': trend['declining_points'],
                        'consecutive_weak_points': trend['consecutive_weak_points'],
                        'knowledge_points': kp_summary,
                    }
            export_data['student_growth_profile'] = knowledge_trend_data

        json_str = json.dumps(export_data, ensure_ascii=False, indent=2, default=str)

        if file_path:
            import os
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            return file_path

        return json_str

    def export_to_csv(self, file_path: Optional[str] = None,
                       include_knowledge_summary: bool = True) -> str:
        """导出合并结果为CSV格式

        包含：排名、学号、姓名、各场成绩、总分、平均分、参考场次、缺考场次、重复提交信息

        Args:
            file_path: 输出文件路径，不传则返回CSV字符串
            include_knowledge_summary: 是否包含知识点掌握概览

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
        header.extend(['总分', '平均分', '参考场次', '缺考场次',
                       '有重复提交', '重复次数', '需人工处理'])

        if include_knowledge_summary:
            all_kps = set()
            for sid in self.student_summary:
                trend = self.get_knowledge_trend(sid)
                if trend:
                    all_kps.update(trend['knowledge_points'].keys())
            sorted_kps = sorted(all_kps)
            for kp in sorted_kps:
                header.append(f'{kp}平均分%')
                header.append(f'{kp}趋势')
                header.append(f'{kp}连续薄弱次数')

        writer.writerow(header)

        student_dup_info = defaultdict(lambda: {'count': 0, 'manual': False})
        for dup in self.duplicates:
            sid = dup['student_id']
            if not dup.get('kept', True):
                continue
            student_dup_info[sid]['count'] += 1
            if dup.get('manual_review_needed'):
                student_dup_info[sid]['manual'] = True

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
            dup_info = student_dup_info.get(s['student_id'], {'count': 0, 'manual': False})
            row.extend([
                s['total_score'],
                s['avg_score'],
                s['exam_count'],
                ','.join([str(x) for x in s['missing_exams']]) if s['missing_exams'] else '',
                '是' if dup_info['count'] > 1 else '否',
                dup_info['count'],
                '是' if dup_info['manual'] else '否',
            ])

            if include_knowledge_summary:
                trend = self.get_knowledge_trend(s['student_id'])
                if trend:
                    for kp in sorted_kps:
                        kp_info = trend['knowledge_points'].get(kp)
                        if kp_info:
                            row.append(round(kp_info['avg_mastery'] * 100, 1))
                            row.append(kp_info['trend'])
                            row.append(kp_info['consecutive_weak_count'])
                        else:
                            row.append('')
                            row.append('')
                            row.append('')

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
