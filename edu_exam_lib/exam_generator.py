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

        if rule.same_questions and rule.num_versions > 1:
            return self._generate_same_questions_versions(rule, seed)

        papers = []
        for version_num in range(1, rule.num_versions + 1):
            version_seed = seed + version_num if seed is not None else None
            paper = self._generate_single_version(rule, version_num, version_seed)
            papers.append(paper)

        return papers

    def _generate_same_questions_versions(self, rule: ExamRule,
                                          seed: Optional[int]) -> List[ExamPaper]:
        """生成同题多卷模式的试卷

        先抽出一批题目，然后各版本只调整题号顺序和选项顺序
        这样A/B/C卷的题目完全相同，只是题号顺序和选项顺序不同
        """
        base_seed = seed if seed is not None else random.randint(1, 1000000)
        random.seed(base_seed)

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

        base_questions = selected_questions[:rule.total_questions]

        papers = []
        for version_num in range(1, rule.num_versions + 1):
            version_seed = base_seed + version_num * 1000
            random.seed(version_seed)

            questions_for_version = base_questions.copy()
            if rule.shuffle_questions:
                random.shuffle(questions_for_version)

            paper_questions = []
            option_mapping = {}
            answer_key = {}
            total_score = 0.0

            for idx, question in enumerate(questions_for_version, start=1):
                processed_q, mapping, new_answer = self._process_question(
                    question, idx, rule.shuffle_options
                )
                paper_questions.append(processed_q)
                option_mapping[question.question_id] = mapping
                answer_key[question.question_id] = new_answer
                total_score += question.score

            paper_id = str(uuid.uuid4())[:8]
            version = chr(64 + version_num) if rule.num_versions > 1 else 'A'

            paper = ExamPaper(
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
        """处理单个题目，包括选项乱序

        选项内容打乱顺序，但标签保持A/B/C/D的顺序。
        例如原始A=def, B=function, C=func, D=define
        乱序后可能变成A=function, B=def, C=define, D=func

        Returns:
            (处理后的题目字典, 原始标签到新标签的映射, 新的正确答案列表)
        """
        original_options = question.options.copy()
        option_labels = [chr(65 + i) for i in range(len(original_options))]
        original_content_by_label = {label: content for label, content in zip(option_labels, original_options)}

        shuffled_options = original_options.copy()
        if shuffle_options and len(original_options) > 1:
            random.shuffle(shuffled_options)

        new_options = {label: content for label, content in zip(option_labels, shuffled_options)}

        original_label_to_new_label = {}
        new_label_to_original_label = {}
        for new_label, new_content in new_options.items():
            for orig_label, orig_content in original_content_by_label.items():
                if new_content == orig_content:
                    original_label_to_new_label[orig_label] = new_label
                    new_label_to_original_label[new_label] = orig_label
                    break

        new_correct_answer = []
        for orig_ans in question.correct_answer:
            new_label = original_label_to_new_label.get(orig_ans)
            if new_label:
                new_correct_answer.append(new_label)

        processed_q = {
            'display_num': display_num,
            'question_id': question.question_id,
            'content': question.content,
            'options': new_options,
            'question_type': question.question_type.value,
            'difficulty': question.difficulty.value,
            'knowledge_points': question.knowledge_points,
            'score': question.score,
        }

        return processed_q, original_label_to_new_label, sorted(new_correct_answer)

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

    def generate_version_comparison(self, papers: List[ExamPaper]) -> str:
        """生成多版本试卷对照

        显示同一道题在不同版本中的题号、选项顺序、正确答案，
        方便老师发卷前抽查有没有乱序错位。

        Args:
            papers: 多份试卷列表（同一套题的不同版本）

        Returns:
            对照报告文本
        """
        if not papers:
            return "没有试卷可对照"

        lines = []
        lines.append("=" * 90)
        lines.append(" " * 35 + "多版本试卷对照表")
        lines.append("=" * 90)
        lines.append("")
        lines.append(f"对照版本: {', '.join([p.version for p in papers])}")
        lines.append(f"题目数量: {len(papers[0].questions)} 题")
        lines.append("")
        lines.append("-" * 90)
        lines.append("")

        all_question_ids = set()
        for p in papers:
            for q in p.questions:
                all_question_ids.add(q['question_id'])

        question_info_by_id = {}
        for p in papers:
            for q in p.questions:
                qid = q['question_id']
                if qid not in question_info_by_id:
                    question_info_by_id[qid] = {
                        'content': q['content'],
                        'question_type': q['question_type'],
                        'score': q['score'],
                        'knowledge_points': q['knowledge_points'],
                    }

        version_question_map = {}
        for p in papers:
            vmap = {}
            for q in p.questions:
                vmap[q['question_id']] = q
            version_question_map[p.version] = vmap

        first_paper = papers[0]
        sorted_question_ids = [q['question_id'] for q in first_paper.questions]

        for idx, qid in enumerate(sorted_question_ids, 1):
            info = question_info_by_id[qid]
            lines.append(f"【第{idx}题 - {qid}】")
            lines.append(f"  题目: {info['content']}")
            lines.append(f"  题型: {info['question_type']}  分值: {info['score']}分  "
                        f"知识点: {', '.join(info['knowledge_points'])}")
            lines.append("")

            header = f"{'版本':<8}"
            header += f"{'题号':<8}"
            header += f"{'正确答案':<12}"
            header += "选项顺序（左→右对应A→D）"
            lines.append(f"  {header}")
            lines.append(f"  {'-' * 80}")

            for p in papers:
                q = version_question_map[p.version].get(qid)
                if q:
                    display_num = q['display_num']
                    correct = "".join(sorted(p.answer_key[qid]))
                    options_list = [q['options'][label] for label in sorted(q['options'].keys())]
                    options_str = " | ".join(options_list)

                    line = f"  {p.version:<8}"
                    line += f"{display_num:<8}"
                    line += f"{correct:<12}"
                    line += options_str
                    lines.append(line)
                else:
                    lines.append(f"  {p.version:<8}  （无此题）")

            lines.append("")
            lines.append(f"  选项映射对照表（原选项 → 新选项）:")
            lines.append(f"    原选项 | {' | '.join([p.version for p in papers])}")
            lines.append(f"    {'-' * 60}")

            original_labels = sorted(first_paper.option_mapping[qid].keys())
            for orig_label in original_labels:
                row = f"    {orig_label}     |"
                for p in papers:
                    new_label = p.option_mapping[qid].get(orig_label, '?')
                    row += f" {new_label}  |"
                lines.append(row)

            lines.append("")
            lines.append("-" * 90)
            lines.append("")

        lines.append("=" * 90)
        lines.append("说明：")
        lines.append("  1. 「正确答案」列显示的是该版本的正确选项字母")
        lines.append("  2. 「选项顺序」列显示各选项的实际内容，从左到右对应A、B、C、D")
        lines.append("  3. 「选项映射对照表」显示原始选项对应到各版本的哪个选项")
        lines.append("  4. 抽查方法：找一道题，核对「正确答案」字母对应「选项顺序」中的内容是否正确")
        lines.append("=" * 90)

        return "\n".join(lines)

    def export_version_comparison(self, papers: List[ExamPaper],
                                  output_dir: str,
                                  file_prefix: str = "exam") -> str:
        """导出版本对照文件（TXT + CSV）"""
        import os
        import csv
        os.makedirs(output_dir, exist_ok=True)

        content = self.generate_version_comparison(papers)
        txt_file = os.path.join(output_dir, f"{file_prefix}_version_comparison.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(content)

        csv_file = os.path.join(output_dir, f"{file_prefix}_version_comparison.csv")
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            header = ['题目ID', '题目内容', '版本', '题号', '正确答案']
            option_labels = sorted(papers[0].questions[0]['options'].keys()) if papers and papers[0].questions else ['A', 'B', 'C', 'D']
            for label in option_labels:
                header.append(f'选项{label}内容')
            header.append('原始选项A映射到')
            header.append('原始选项B映射到')
            header.append('原始选项C映射到')
            header.append('原始选项D映射到')
            writer.writerow(header)

            all_question_ids = []
            seen_ids = set()
            for p in papers:
                for q in p.questions:
                    if q['question_id'] not in seen_ids:
                        all_question_ids.append(q['question_id'])
                        seen_ids.add(q['question_id'])

            version_question_map = {}
            for p in papers:
                vmap = {}
                for q in p.questions:
                    vmap[q['question_id']] = q
                version_question_map[p.version] = vmap

            for qid in all_question_ids:
                for p in papers:
                    q = version_question_map[p.version].get(qid)
                    if q:
                        correct = "".join(sorted(p.answer_key[qid]))
                        row = [qid, q['content'], p.version, q['display_num'], correct]
                        for label in option_labels:
                            row.append(q['options'].get(label, ''))
                        orig_labels = ['A', 'B', 'C', 'D']
                        for orig in orig_labels:
                            mapped = p.option_mapping.get(qid, {}).get(orig, '')
                            row.append(mapped)
                        writer.writerow(row)

        return txt_file
