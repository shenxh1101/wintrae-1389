"""
教育测评系统类库
提供题库管理、试卷生成、答题卡生成、客观题判分、统计分析等功能
"""

from .core import (
    Question,
    ExamRule,
    ExamPaper,
    ExamResult,
    StudentAnswer,
    DifficultyLevel,
    QuestionType,
    QuestionResult,
    MergeResult,
)
from .question_bank import QuestionBank
from .exam_generator import ExamGenerator
from .grader import ExamGrader
from .statistics import ExamStatistics
from .exam_system import ExamSystem
from .api import generate_exam, grade_exam, analyze_results

__all__ = [
    'Question',
    'ExamRule',
    'ExamPaper',
    'ExamResult',
    'StudentAnswer',
    'DifficultyLevel',
    'QuestionType',
    'QuestionResult',
    'MergeResult',
    'QuestionBank',
    'ExamGenerator',
    'ExamGrader',
    'ExamStatistics',
    'ExamSystem',
    'generate_exam',
    'grade_exam',
    'analyze_results',
]

__version__ = '1.0.0'
