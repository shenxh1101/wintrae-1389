"""
核心数据结构定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import uuid


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
    answers: Dict[str, List[str]]
    submitted_at: Optional[str] = None

    def __post_init__(self):
        normalized = {}
        for qid, ans in self.answers.items():
            if isinstance(ans, str):
                normalized[qid] = [ans.upper()]
            else:
                normalized[qid] = [a.upper() for a in ans]
        self.answers = normalized

    def validate(self, exam_paper: ExamPaper) -> Tuple[bool, List[str]]:
        """验证答案与试卷是否匹配"""
        errors = []
        question_ids = {q['question_id'] for q in exam_paper.questions}

        for qid in self.answers:
            if qid not in question_ids:
                errors.append(f"题号 {qid} 不在试卷中")

        seen = set()
        for qid in self.answers:
            if qid in seen:
                errors.append(f"题号 {qid} 重复")
            seen.add(qid)

        return len(errors) == 0, errors


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

    def to_dict(self) -> Dict[str, Any]:
        return {
            'merged_results': [r.to_dict() for r in self.merged_results],
            'duplicates': self.duplicates,
            'missing_answers': self.missing_answers,
            'errors': self.errors,
        }
