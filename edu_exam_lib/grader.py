"""
判分模块
"""

from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from collections import defaultdict
from .core import ExamPaper, StudentAnswer, ExamResult, QuestionResult, MergeResult


class ExamGrader:
    """考试判分类"""

    def __init__(self, exam_paper: ExamPaper):
        self.exam_paper = exam_paper
        self._question_map = {q['question_id']: q for q in exam_paper.questions}

    def grade(self, student_answer: StudentAnswer) -> ExamResult:
        """对学生答案进行判分"""
        if student_answer.has_duplicates:
            dup_detail = ", ".join(
                f"{qid}(出现{student_answer._question_id_counts[qid]}次)" 
                for qid in student_answer.duplicate_question_ids
            )
            raise ValueError(
                f"检测到重复题号，无法进行批改。请先修正重复答案后再提交。"
                f"重复题号: {dup_detail}"
            )

        is_valid, errors, missing = student_answer.validate(self.exam_paper)
        if not is_valid:
            raise ValueError(f"学生答案无效: {'; '.join(errors)}")

        if missing:
            raise ValueError(
                f"存在缺失答案的题目: {', '.join(missing)}"
            )

        question_results = []
        total_score = 0.0
        max_score = 0.0

        for q in self.exam_paper.questions:
            qid = q['question_id']
            correct_answer = self.exam_paper.answer_key.get(qid, [])
            student_ans = student_answer.answers.get(qid, [])

            is_correct = sorted(student_ans) == sorted(correct_answer)
            score = q['score'] if is_correct else 0.0

            total_score += score
            max_score += q['score']

            qr = QuestionResult(
                question_id=qid,
                student_answer=student_ans,
                correct_answer=correct_answer,
                is_correct=is_correct,
                score=score,
                max_score=q['score'],
                knowledge_points=q['knowledge_points'],
                difficulty=q['difficulty'],
            )
            question_results.append(qr)

        knowledge_mastery = self._calculate_knowledge_mastery(question_results)
        error_reasons = self._analyze_errors(question_results)

        percentage = (total_score / max_score * 100) if max_score > 0 else 0.0

        return ExamResult(
            student_id=student_answer.student_id,
            student_name=student_answer.student_name,
            paper_id=self.exam_paper.paper_id,
            total_score=total_score,
            max_score=max_score,
            percentage=round(percentage, 2),
            question_results=question_results,
            knowledge_mastery=knowledge_mastery,
            error_reasons=error_reasons,
            graded_at=datetime.now().isoformat(),
        )

    def _calculate_knowledge_mastery(
            self,
            question_results: List[QuestionResult]
    ) -> Dict[str, Dict[str, float]]:
        """计算各知识点的掌握情况"""
        kp_stats: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {'correct': 0, 'total': 0, 'score': 0, 'max_score': 0}
        )

        for qr in question_results:
            for kp in qr.knowledge_points:
                kp_stats[kp]['total'] += 1
                kp_stats[kp]['max_score'] += qr.max_score
                if qr.is_correct:
                    kp_stats[kp]['correct'] += 1
                    kp_stats[kp]['score'] += qr.score

        mastery: Dict[str, Dict[str, float]] = {}
        for kp, stats in kp_stats.items():
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            score_rate = (stats['score'] / stats['max_score'] * 100) if stats['max_score'] > 0 else 0
            mastery[kp] = {
                'accuracy': round(accuracy, 2),
                'score_rate': round(score_rate, 2),
                'correct_count': stats['correct'],
                'total_count': stats['total'],
                'score': stats['score'],
                'max_score': stats['max_score'],
            }

        return mastery

    def _analyze_errors(
            self,
            question_results: List[QuestionResult]
    ) -> List[Dict[str, Any]]:
        """错题归因分析"""
        errors = []
        for qr in question_results:
            if qr.is_correct:
                continue

            reason = self._determine_error_reason(qr)
            errors.append({
                'question_id': qr.question_id,
                'student_answer': qr.student_answer,
                'correct_answer': qr.correct_answer,
                'reason': reason,
                'knowledge_points': qr.knowledge_points,
                'difficulty': qr.difficulty,
                'lost_score': qr.max_score,
            })

        return errors

    def _determine_error_reason(self, qr: QuestionResult) -> str:
        """判断错误原因"""
        if not qr.student_answer:
            return "未作答"

        if len(qr.correct_answer) > 1 and len(qr.student_answer) < len(qr.correct_answer):
            return "漏选"

        if len(qr.student_answer) > len(qr.correct_answer):
            return "多选"

        if qr.difficulty == 'hard':
            return "难度较高"

        common = set(qr.student_answer) & set(qr.correct_answer)
        if common:
            return "部分错误"

        return "概念混淆/知识盲区"

    def grade_batch(self, student_answers: List[StudentAnswer]) -> List[ExamResult]:
        """批量判分"""
        results = []
        for sa in student_answers:
            try:
                result = self.grade(sa)
                results.append(result)
            except ValueError as e:
                raise ValueError(f"学生 {sa.student_name}({sa.student_id}) 判分失败: {e}")
        return results

    def validate_answers(self, student_answer: StudentAnswer) -> Tuple[bool, List[str], List[str]]:
        """验证学生答案，返回是否有效、错误列表、缺失题目列表"""
        return student_answer.validate(self.exam_paper)

    def generate_grade_report(self, result: ExamResult) -> str:
        """生成判分报告文本"""
        lines = []
        lines.append("=" * 70)
        lines.append(" " * 25 + "考试成绩报告单")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"学生姓名: {result.student_name}    学号: {result.student_id}")
        lines.append(f"试卷ID: {result.paper_id}")
        lines.append(f"判分时间: {result.graded_at}")
        lines.append("")
        lines.append("-" * 70)
        lines.append("")
        lines.append(f"总分: {result.total_score:.1f} / {result.max_score:.1f}    "
                      f"得分率: {result.percentage:.1f}%")
        lines.append("")
        lines.append("-" * 70)
        lines.append("")
        lines.append("一、各题得分情况")
        lines.append("")

        for i, qr in enumerate(result.question_results, 1):
            status = "✓ 正确" if qr.is_correct else "✗ 错误"
            sa = "".join(qr.student_answer) if qr.student_answer else "(空)"
            ca = "".join(qr.correct_answer)
            kp = ", ".join(qr.knowledge_points)
            lines.append(
                f"{i:>2}. 题号{qr.question_id}  {status}  "
                f"得分: {qr.score:.1f}/{qr.max_score:.1f}  "
                f"学生答案: {sa}  正确答案: {ca}  "
                f"知识点: {kp}"
            )

        lines.append("")
        lines.append("-" * 70)
        lines.append("")
        lines.append("二、知识点掌握情况")
        lines.append("")

        sorted_mastery = sorted(
            result.knowledge_mastery.items(),
            key=lambda x: x[1]['accuracy'],
            reverse=True
        )
        for kp, stats in sorted_mastery:
            bar_len = int(stats['accuracy'] / 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            lines.append(
                f"{kp:<20} {bar}  {stats['accuracy']:>5.1f}%  "
                f"({stats['correct_count']}/{stats['total_count']}题, "
                f"{stats['score']:.1f}/{stats['max_score']:.1f}分)"
            )

        if result.error_reasons:
            lines.append("")
            lines.append("-" * 70)
            lines.append("")
            lines.append("三、错题分析")
            lines.append("")

            for i, err in enumerate(result.error_reasons, 1):
                sa = "".join(err['student_answer']) if err['student_answer'] else "(空)"
                ca = "".join(err['correct_answer'])
                kp = ", ".join(err['knowledge_points'])
                lines.append(
                    f"{i:>2}. 题号{err['question_id']}  "
                    f"错误原因: {err['reason']}  "
                    f"学生答案: {sa}  正确答案: {ca}  "
                    f"知识点: {kp}  失分: {err['lost_score']:.1f}分"
                )

        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    @staticmethod
    def merge_exam_results(results_list: List[List[ExamResult]]) -> MergeResult:
        """合并多场考试结果"""
        merged: List[ExamResult] = []
        duplicates: List[Dict[str, Any]] = []
        missing_answers: List[Dict[str, Any]] = []
        errors: List[str] = []

        exam_info = []
        for exam_idx, results in enumerate(results_list, 1):
            if results:
                exam_info.append({
                    'exam_index': exam_idx,
                    'paper_id': results[0].paper_id,
                    'student_count': len(results),
                    'max_score': results[0].max_score,
                })
            else:
                exam_info.append({
                    'exam_index': exam_idx,
                    'paper_id': f'unknown_{exam_idx}',
                    'student_count': 0,
                    'max_score': 0,
                })

        seen = defaultdict(list)

        for exam_idx, results in enumerate(results_list, 1):
            for result in results:
                key = (result.student_id, result.paper_id)
                seen[key].append({
                    'exam_index': exam_idx,
                    'result': result,
                })

        for (student_id, paper_id), entries in seen.items():
            if len(entries) > 1:
                for entry in entries:
                    duplicates.append({
                        'student_id': student_id,
                        'student_name': entry['result'].student_name,
                        'paper_id': paper_id,
                        'exam_index': entry['exam_index'],
                        'score': entry['result'].total_score,
                    })
                errors.append(
                    f"学生 {student_id} 在试卷 {paper_id} 有 {len(entries)} 条重复记录"
                )
                merged.append(entries[0]['result'])
            else:
                merged.append(entries[0]['result'])

        merged.sort(key=lambda x: x.student_id)

        student_summary = {}
        student_exams = defaultdict(dict)

        for exam_idx, results in enumerate(results_list, 1):
            for result in results:
                sid = result.student_id
                if sid not in student_summary:
                    student_summary[sid] = {
                        'student_id': sid,
                        'student_name': result.student_name,
                        'total_score': 0.0,
                        'max_possible_score': 0.0,
                        'avg_score': 0.0,
                        'exam_count': 0,
                        'exam_scores': [],
                        'missing_exams': [],
                    }
                student_exams[sid][exam_idx] = result

        for sid, summary in student_summary.items():
            total_score = 0.0
            max_possible = 0.0
            exam_count = 0
            exam_scores = []
            missing_exams = []

            for exam_idx in range(1, len(results_list) + 1):
                info = exam_info[exam_idx - 1]
                if exam_idx in student_exams[sid]:
                    result = student_exams[sid][exam_idx]
                    exam_scores.append({
                        'exam_index': exam_idx,
                        'paper_id': result.paper_id,
                        'score': result.total_score,
                        'max_score': result.max_score,
                        'percentage': round(result.percentage, 1),
                        'has_score': True,
                    })
                    total_score += result.total_score
                    max_possible += result.max_score
                    exam_count += 1
                else:
                    exam_scores.append({
                        'exam_index': exam_idx,
                        'paper_id': info['paper_id'],
                        'score': 0,
                        'max_score': info['max_score'],
                        'percentage': 0,
                        'has_score': False,
                    })
                    missing_exams.append(exam_idx)

            summary['total_score'] = round(total_score, 1)
            summary['max_possible_score'] = round(max_possible, 1)
            summary['avg_score'] = round(total_score / exam_count, 1) if exam_count > 0 else 0.0
            summary['exam_count'] = exam_count
            summary['exam_scores'] = exam_scores
            summary['missing_exams'] = missing_exams

        return MergeResult(
            merged_results=merged,
            duplicates=duplicates,
            missing_answers=missing_answers,
            errors=errors,
            exam_info=exam_info,
            student_summary=student_summary,
        )
