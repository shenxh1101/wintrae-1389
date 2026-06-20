"""
试卷生成模块
"""

from typing import List, Dict, Tuple, Optional, Any
import random
import uuid
from datetime import datetime
from collections import defaultdict
from .core import Question, ExamRule, ExamPaper, DifficultyLevel, QuestionType
from .question_bank import QuestionBank


class ExamGenerator:
    """试卷生成器"""

    def __init__(self, question_bank: QuestionBank):
        self.question_bank = question_bank

    def generate_exam(self, rule: ExamRule,
                      seed: Optional[int] = None) -> List[ExamPaper]:
        """根据规则生成试卷（支持多版本）"""
        is_valid, errors = rule.validate()
        if not is_valid:
            raise ValueError(f"组卷规则无效: {'; '.join(errors)}")

        if seed is not None:
            random.seed(seed)

        papers = []
        for version_num in range(1, rule.num_versions + 1):
            version_seed = seed + version_num if seed is not None else None
            paper = self._generate_single_version(rule, version_num, version_seed)
            papers.append(paper)

        return papers

    def _generate_single_version(self, rule: ExamRule,
                                 version_num: int,
                                 seed: Optional[int]) -> ExamPaper:
        """生成单个版本的试卷"""
        if seed is not None:
            random.seed(seed)

        candidate_questions = self.question_bank.filter_complex(
            knowledge_points=rule.allowed_knowledge_points,
            exclude_knowledge=rule.excluded_knowledge_points,
        )

        if rule.knowledge_points:
            selected_questions = self.question_bank.select_by_knowledge_points(
                rule.knowledge_points, rule.difficulty_ratio
            )
        else:
            selected_questions = self.question_bank.select_by_difficulty_ratio(
                candidate_questions,
                rule.total_questions,
                rule.difficulty_ratio
            )

        if len(selected_questions) < rule.total_questions:
            raise ValueError(
                f"题库中符合条件的题目不足，需要 {rule.total_questions} 道，"
                f"实际只有 {len(selected_questions)} 道"
            )

        if rule.shuffle_questions:
            random.shuffle(selected_questions)

        paper_questions = []
        option_mapping = {}
        answer_key = {}
        total_score = 0.0

        for idx, question in enumerate(selected_questions, start=1):
            processed_q, mapping, new_answer = self._process_question(
                question, idx, rule.shuffle_options
            )
            paper_questions.append(processed_q)
            option_mapping[question.question_id] = mapping
            answer_key[question.question_id] = new_answer
            total_score += question.score

        paper_id = str(uuid.uuid4())[:8]
        version = chr(64 + version_num) if rule.num_versions > 1 else 'A'

        return ExamPaper(
            paper_id=paper_id,
            version=version,
            title=rule.exam_title,
            duration=rule.exam_duration,
            questions=paper_questions,
            option_mapping=option_mapping,
            answer_key=answer_key,
            generated_at=datetime.now().isoformat(),
            total_score=total_score,
        )

    def _process_question(self, question: Question, display_num: int,
                          shuffle_options: bool) -> Tuple[Dict[str, Any],
                                                          Dict[str, str],
                                                          List[str]]:
        """处理单个题目，包括选项乱序"""
        options = question.options.copy()
        option_labels = [chr(65 + i) for i in range(len(options))]

        original_mapping = {label: opt for label, opt in zip(option_labels, options)}

        if shuffle_options and len(options) > 1:
            paired = list(zip(option_labels, options))
            random.shuffle(paired)
            option_labels, options = zip(*paired)

        new_mapping = {}
        for i, (orig_label, new_label) in enumerate(
                zip(original_mapping.keys(), option_labels)):
            new_mapping[new_label] = orig_label

        new_correct_answer = []
        for orig_ans in question.correct_answer:
            for new_label, orig_label in new_mapping.items():
                if orig_label == orig_ans:
                    new_correct_answer.append(new_label)
                    break

        processed_q = {
            'display_num': display_num,
            'question_id': question.question_id,
            'content': question.content,
            'options': {label: opt for label, opt in zip(option_labels, options)},
            'question_type': question.question_type.value,
            'difficulty': question.difficulty.value,
            'knowledge_points': question.knowledge_points,
            'score': question.score,
        }

        reverse_mapping = {v: k for k, v in new_mapping.items()}
        return processed_q, reverse_mapping, sorted(new_correct_answer)

    def generate_answer_sheet(self, exam_paper: ExamPaper,
                              include_options: bool = True) -> str:
        """生成答题卡文本"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"{exam_paper.title} - 答题卡")
        lines.append(f"试卷版本: {exam_paper.version}")
        lines.append(f"试卷ID: {exam_paper.paper_id}")
        lines.append("=" * 60)
        lines.append("")
        lines.append("姓名: _______________    学号: _______________")
        lines.append("班级: _______________    得分: _______________")
        lines.append("")
        lines.append("-" * 60)
        lines.append("")

        for q in exam_paper.questions:
            num = q['display_num']
            qid = q['question_id']
            q_type = q['question_type']
            score = q['score']

            type_str = {
                'single_choice': '单选',
                'multiple_choice': '多选',
                'true_false': '判断',
            }.get(q_type, '选择题')

            lines.append(f"{num}. ({type_str}, {score}分)  答案: __________")

            if include_options:
                for label in sorted(q['options'].keys()):
                    lines.append(f"    {label}. {q['options'][label]}")
                lines.append("")

        lines.append("")
        lines.append("-" * 60)
        lines.append("* 多选题请将所有正确选项填入横线，如：ABC")
        lines.append("=" * 60)

        return "\n".join(lines)

    def generate_answer_key(self, exam_paper: ExamPaper) -> str:
        """生成标准答案文本"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"{exam_paper.title} - 标准答案")
        lines.append(f"试卷版本: {exam_paper.version}")
        lines.append(f"试卷ID: {exam_paper.paper_id}")
        lines.append(f"生成时间: {exam_paper.generated_at}")
        lines.append("=" * 60)
        lines.append("")

        total_score = 0
        for q in exam_paper.questions:
            num = q['display_num']
            qid = q['question_id']
            answer = exam_paper.answer_key.get(qid, [])
            score = q['score']
            total_score += score

            answer_str = "".join(sorted(answer))
            lines.append(f"{num}. {answer_str}  ({score}分)")

        lines.append("")
        lines.append(f"总分: {total_score}分")
        lines.append("=" * 60)

        return "\n".join(lines)

    def generate_printable_exam(self, exam_paper: ExamPaper) -> str:
        """生成可打印的试卷文本"""
        lines = []
        lines.append("=" * 70)
        lines.append(" " * 20 + exam_paper.title)
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"试卷版本: {exam_paper.version}    考试时间: {exam_paper.duration}分钟")
        lines.append(f"试卷ID: {exam_paper.paper_id}")
        lines.append("")
        lines.append("姓名: _______________    学号: _______________    班级: _______________")
        lines.append("")
        lines.append("-" * 70)
        lines.append("")
        lines.append("一、选择题（本大题共{}小题，每题分数见题后标注，总分{}分）".format(
            len(exam_paper.questions), exam_paper.total_score))
        lines.append("")

        for q in exam_paper.questions:
            num = q['display_num']
            q_type = q['question_type']
            score = q['score']

            type_str = {
                'single_choice': '单选题',
                'multiple_choice': '多选题',
                'true_false': '判断题',
            }.get(q_type, '选择题')

            lines.append(f"{num}. （{type_str}，{score}分）{q['content']}")
            lines.append("")

            for label in sorted(q['options'].keys()):
                text = q['options'][label]
                if len(text) > 60:
                    lines.append(f"    {label}. {text}")
                else:
                    lines.append(f"    {label}. {text:<30}")
            lines.append("")
            lines.append("    答：__________")
            lines.append("")

        lines.append("")
        lines.append("=" * 70)
        lines.append("")
        lines.append("答题说明：")
        lines.append("1. 请将答案写在每题后的横线处")
        lines.append("2. 多选题请填写所有正确选项字母，如ABC")
        lines.append("3. 考试结束后请将试卷和答题卡一并上交")
        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    def generate_printable_answer_sheet(self, exam_paper: ExamPaper) -> str:
        """生成可打印的答题卡（独立版本）"""
        lines = []
        lines.append("=" * 70)
        lines.append(" " * 25 + "答 题 卡")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"考试名称: {exam_paper.title}")
        lines.append(f"试卷版本: {exam_paper.version}    试卷ID: {exam_paper.paper_id}")
        lines.append("")
        lines.append("-" * 70)
        lines.append("")
        lines.append("姓名: ___________________    学号: ___________________")
        lines.append("班级: ___________________    考场: ___________________")
        lines.append("")
        lines.append("-" * 70)
        lines.append("")
        lines.append("选择题答题区")
        lines.append("")

        questions = exam_paper.questions
        cols = 4
        rows = (len(questions) + cols - 1) // cols

        header = "| " + " | ".join([f"  题号  答案  " for _ in range(cols)]) + " |"
        separator = "+" + "+".join(["-" * 14 for _ in range(cols)]) + "+"

        lines.append(separator)
        lines.append(header)
        lines.append(separator)

        for row in range(rows):
            row_cells = []
            for col in range(cols):
                idx = row * cols + col
                if idx < len(questions):
                    q = questions[idx]
                    cell = f"  {q['display_num']:>2}.   ________  "
                else:
                    cell = "                 "
                row_cells.append(cell)
            lines.append("|" + "|".join(row_cells) + "|")
            lines.append(separator)

        lines.append("")
        lines.append("-" * 70)
        lines.append("")
        lines.append("填涂说明：")
        lines.append("[ ] 单选题填一个选项  [ ] 多选题填多个选项  [ ] 判断题填√或×")
        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    def export_paper_to_files(self, exam_paper: ExamPaper,
                              output_dir: str,
                              file_prefix: str = "exam") -> Dict[str, str]:
        """导出生成的试卷、答题卡、答案到文件"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        base_name = f"{file_prefix}_{exam_paper.version}_{exam_paper.paper_id}"

        files = {}

        exam_file = os.path.join(output_dir, f"{base_name}_paper.txt")
        with open(exam_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_printable_exam(exam_paper))
        files['paper'] = exam_file

        answer_sheet_file = os.path.join(output_dir, f"{base_name}_answer_sheet.txt")
        with open(answer_sheet_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_printable_answer_sheet(exam_paper))
        files['answer_sheet'] = answer_sheet_file

        answer_key_file = os.path.join(output_dir, f"{base_name}_answer_key.txt")
        with open(answer_key_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_answer_key(exam_paper))
        files['answer_key'] = answer_key_file

        return files
