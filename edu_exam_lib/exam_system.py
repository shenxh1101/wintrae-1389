"""
考试系统主入口类
整合题库管理、试卷生成、判分、统计等功能
"""

from typing import List, Dict, Optional, Tuple, Any
from .core import Question, ExamRule, ExamPaper, StudentAnswer, ExamResult, MergeResult
from .question_bank import QuestionBank
from .exam_generator import ExamGenerator
from .grader import ExamGrader
from .statistics import ExamStatistics


class ExamSystem:
    """考试系统主类"""

    def __init__(self):
        self.question_bank = QuestionBank()
        self._exam_papers: Dict[str, ExamPaper] = {}
        self._results: Dict[str, List[ExamResult]] = {}

    def import_questions(self, questions: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        """导入题目列表"""
        q_objs = []
        for q_data in questions:
            try:
                q_objs.append(Question.from_dict(q_data))
            except Exception as e:
                raise ValueError(f"题目数据格式错误: {e}")

        errors = self.question_bank.add_questions(q_objs)
        return len(q_objs) - len(errors), errors

    def import_questions_from_file(self, file_path: str) -> Tuple[int, List[str]]:
        """从文件导入题目（支持JSON和CSV）"""
        if file_path.lower().endswith('.json'):
            return self.question_bank.import_from_json(file_path)
        elif file_path.lower().endswith('.csv'):
            return self.question_bank.import_from_csv(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_path}")

    def generate_exam(self, rule: ExamRule,
                      seed: Optional[int] = None) -> List[ExamPaper]:
        """生成试卷"""
        generator = ExamGenerator(self.question_bank)
        papers = generator.generate_exam(rule, seed=seed)

        for paper in papers:
            self._exam_papers[paper.paper_id] = paper

        return papers

    def get_exam_paper(self, paper_id: str) -> Optional[ExamPaper]:
        """获取试卷"""
        return self._exam_papers.get(paper_id)

    def grade_exam(self, paper_id: str,
                   student_answers: List[Dict[str, Any]]) -> List[ExamResult]:
        """批改试卷"""
        paper = self.get_exam_paper(paper_id)
        if paper is None:
            raise ValueError(f"试卷不存在: {paper_id}")

        grader = ExamGrader(paper)
        sa_objs = []

        for sa_data in student_answers:
            try:
                sa = StudentAnswer(**sa_data)
                is_valid, errors, missing = grader.validate_answers(sa)
                if not is_valid:
                    raise ValueError("; ".join(errors))
                if missing:
                    raise ValueError(f"存在缺失答案的题目: {', '.join(missing)}")
                sa_objs.append(sa)
            except ValueError as e:
                raise ValueError(f"学生答案错误 - {sa_data.get('student_name', '未知')}"
                                 f"({sa_data.get('student_id', '未知')}): {e}")

        results = grader.grade_batch(sa_objs)

        if paper_id not in self._results:
            self._results[paper_id] = []
        self._results[paper_id].extend(results)

        return results

    def get_results(self, paper_id: str) -> List[ExamResult]:
        """获取指定试卷的所有结果"""
        return self._results.get(paper_id, [])

    def analyze_results(self, paper_id: str) -> ExamStatistics:
        """分析试卷结果"""
        results = self.get_results(paper_id)
        if not results:
            raise ValueError(f"试卷 {paper_id} 没有判分结果")
        return ExamStatistics(results)

    def merge_exam_results(self, paper_ids: List[str]) -> MergeResult:
        """合并多场考试结果"""
        results_list = []
        for pid in paper_ids:
            results = self.get_results(pid)
            if not results:
                raise ValueError(f"试卷 {pid} 没有判分结果")
            results_list.append(results)

        return ExamGrader.merge_exam_results(results_list)

    def generate_printable_content(self, paper_id: str,
                                    content_type: str = 'paper') -> str:
        """生成可打印内容"""
        paper = self.get_exam_paper(paper_id)
        if paper is None:
            raise ValueError(f"试卷不存在: {paper_id}")

        generator = ExamGenerator(self.question_bank)

        type_map = {
            'paper': generator.generate_printable_exam,
            'answer_sheet': generator.generate_printable_answer_sheet,
            'answer_key': generator.generate_answer_key,
        }

        if content_type not in type_map:
            raise ValueError(f"不支持的内容类型: {content_type}")

        return type_map[content_type](paper)

    def export_to_files(self, paper_id: str, output_dir: str,
                         file_prefix: str = "exam") -> Dict[str, str]:
        """导出试卷相关文件"""
        paper = self.get_exam_paper(paper_id)
        if paper is None:
            raise ValueError(f"试卷不存在: {paper_id}")

        generator = ExamGenerator(self.question_bank)
        return generator.export_paper_to_files(paper, output_dir, file_prefix)

    def generate_grade_report(self, result: ExamResult) -> str:
        """生成个人成绩报告"""
        paper = self.get_exam_paper(result.paper_id)
        if paper is None:
            raise ValueError(f"试卷不存在: {result.paper_id}")

        grader = ExamGrader(paper)
        return grader.generate_grade_report(result)

    def validate_student_answer(self, paper_id: str,
                                 student_answer: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """验证学生答案是否有效"""
        paper = self.get_exam_paper(paper_id)
        if paper is None:
            raise ValueError(f"试卷不存在: {paper_id}")

        grader = ExamGrader(paper)
        sa = StudentAnswer(**student_answer)
        return grader.validate_answers(sa)

    def get_bank_stats(self) -> Dict[str, Any]:
        """获取题库统计信息"""
        return {
            'total_questions': len(self.question_bank),
            'knowledge_points': self.question_bank.get_knowledge_points(),
            'knowledge_distribution': self.question_bank.get_knowledge_distribution(),
            'difficulty_distribution': self.question_bank.get_difficulty_distribution(),
            'type_distribution': self.question_bank.get_type_distribution(),
        }

    def list_exam_papers(self) -> List[Dict[str, Any]]:
        """列出所有试卷"""
        return [
            {
                'paper_id': pid,
                'version': p.version,
                'title': p.title,
                'num_questions': len(p.questions),
                'total_score': p.total_score,
                'generated_at': p.generated_at,
                'result_count': len(self._results.get(pid, [])),
            }
            for pid, p in self._exam_papers.items()
        ]
