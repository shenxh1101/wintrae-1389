"""
简单API函数
提供便捷的函数调用接口
"""

from typing import List, Dict, Optional, Any, Tuple
from .core import Question, ExamRule, ExamPaper, StudentAnswer, ExamResult
from .question_bank import QuestionBank
from .exam_generator import ExamGenerator
from .grader import ExamGrader
from .statistics import ExamStatistics
from .exam_system import ExamSystem


def generate_exam(
    questions: List[Dict[str, Any]],
    rule: Dict[str, Any],
    seed: Optional[int] = None
) -> Tuple[List[ExamPaper], Dict[str, Any]]:
    """
    根据题目列表和组卷规则生成试卷

    Args:
        questions: 题目列表，每项为题目的字典表示
        rule: 组卷规则字典
        seed: 随机种子，用于复现结果

    Returns:
        (试卷列表, 题库统计信息)

    Raises:
        ValueError: 当题目或规则无效时抛出
    """
    system = ExamSystem()
    count, errors = system.import_questions(questions)
    if errors:
        raise ValueError(f"导入题目失败: {'; '.join(errors)}")

    rule_obj = ExamRule(**rule)
    papers = system.generate_exam(rule_obj, seed=seed)
    bank_stats = system.get_bank_stats()

    return papers, bank_stats


def grade_exam(
    exam_paper: ExamPaper,
    student_answers: List[Dict[str, Any]],
    questions: Optional[List[Dict[str, Any]]] = None
) -> Tuple[List[ExamResult], Dict[str, Any]]:
    """
    批改学生答案

    Args:
        exam_paper: 试卷对象
        student_answers: 学生答案列表
        questions: 原始题目列表（可选，用于补充题库）

    Returns:
        (判分结果列表, 验证信息)

    Raises:
        ValueError: 当答案无效时抛出
    """
    system = ExamSystem()

    if questions:
        system.import_questions(questions)

    system._exam_papers[exam_paper.paper_id] = exam_paper

    validation_info = {
        'total_students': len(student_answers),
        'valid_answers': 0,
        'errors': [],
    }

    valid_answers = []
    for idx, sa in enumerate(student_answers):
        try:
            is_valid, errors, missing = system.validate_student_answer(
                exam_paper.paper_id, sa
            )
            if not is_valid:
                validation_info['errors'].append(
                    f"学生{idx + 1}({sa.get('student_name', '未知')}): {'; '.join(errors)}"
                )
                continue
            if missing:
                validation_info['errors'].append(
                    f"学生{idx + 1}({sa.get('student_name', '未知')})"
                    f"缺失答案: {', '.join(missing)}"
                )
                continue
            valid_answers.append(sa)
        except Exception as e:
            validation_info['errors'].append(
                f"学生{idx + 1}({sa.get('student_name', '未知')}): {str(e)}"
            )
            continue

    validation_info['valid_answers'] = len(valid_answers)

    if not valid_answers:
        raise ValueError(
            f"没有有效的学生答案。错误: {'; '.join(validation_info['errors'])}"
        )

    results = system.grade_exam(exam_paper.paper_id, valid_answers)
    return results, validation_info


def analyze_results(
    exam_results: List[ExamResult],
    allow_multi_paper: bool = False
) -> Dict[str, Any]:
    """
    分析考试结果

    Args:
        exam_results: 判分结果列表
        allow_multi_paper: 是否允许跨试卷统计

    Returns:
        包含各种统计信息的字典
    """
    stats = ExamStatistics(exam_results, allow_multi_paper=allow_multi_paper)

    result = {
        'descriptive': stats.get_descriptive_stats(),
        'score_distribution': stats.get_score_distribution(),
        'knowledge_points': stats.get_knowledge_point_stats(),
        'questions': stats.get_question_stats(),
        'error_reasons': stats.get_error_reason_stats(),
        'ranking': stats.rank_students(),
        'report': stats.generate_statistics_report(),
        'is_multi_paper': stats.is_multi_paper,
        'paper_ids': stats.paper_ids,
    }

    if stats.is_multi_paper:
        result['multi_paper_summary'] = stats.get_multi_paper_summary()
        result['multi_paper_report'] = stats.generate_multi_paper_report()

    return result
