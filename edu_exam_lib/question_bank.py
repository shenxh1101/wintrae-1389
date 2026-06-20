"""
题库管理模块
"""

from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import json
import csv
import os
from .core import Question, DifficultyLevel, QuestionType


class QuestionBank:
    """题库管理类"""

    def __init__(self):
        self._questions: Dict[str, Question] = {}
        self._by_knowledge: Dict[str, List[str]] = defaultdict(list)
        self._by_difficulty: Dict[DifficultyLevel, List[str]] = defaultdict(list)
        self._by_type: Dict[QuestionType, List[str]] = defaultdict(list)
        self._by_tag: Dict[str, List[str]] = defaultdict(list)

    def add_question(self, question: Question) -> None:
        """添加单个题目"""
        if question.question_id in self._questions:
            raise ValueError(f"题目ID {question.question_id} 已存在")

        self._questions[question.question_id] = question

        for kp in question.knowledge_points:
            self._by_knowledge[kp].append(question.question_id)

        self._by_difficulty[question.difficulty].append(question.question_id)
        self._by_type[question.question_type].append(question.question_id)

        for tag in question.tags:
            self._by_tag[tag].append(question.question_id)

    def add_questions(self, questions: List[Question]) -> List[str]:
        """批量添加题目，返回添加失败的题目ID列表"""
        errors = []
        for q in questions:
            try:
                self.add_question(q)
            except ValueError as e:
                errors.append(str(e))
        return errors

    def import_from_json(self, file_path: str) -> Tuple[int, List[str]]:
        """从JSON文件导入题库"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and 'questions' in data:
            data = data['questions']

        if not isinstance(data, list):
            raise ValueError("JSON格式错误，应为题目列表或包含questions字段的对象")

        questions = []
        for item in data:
            try:
                questions.append(Question.from_dict(item))
            except Exception as e:
                raise ValueError(f"题目数据格式错误: {e}")

        errors = self.add_questions(questions)
        return len(questions) - len(errors), errors

    def import_from_csv(self, file_path: str) -> Tuple[int, List[str]]:
        """从CSV文件导入题库"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        questions = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    options = self._parse_csv_list(row.get('options', ''))
                    correct_answer = self._parse_csv_list(row.get('correct_answer', ''))
                    knowledge_points = self._parse_csv_list(row.get('knowledge_points', ''))
                    tags = self._parse_csv_list(row.get('tags', ''))

                    q = Question(
                        question_id=row.get('question_id', ''),
                        content=row.get('content', ''),
                        options=options,
                        correct_answer=correct_answer,
                        knowledge_points=knowledge_points,
                        difficulty=row.get('difficulty', 'medium'),
                        question_type=row.get('question_type', 'single_choice'),
                        score=float(row.get('score', '1.0')),
                        explanation=row.get('explanation', ''),
                        tags=tags,
                    )
                    questions.append(q)
                except Exception as e:
                    raise ValueError(f"第 {row_num} 行格式错误: {e}")

        errors = self.add_questions(questions)
        return len(questions) - len(errors), errors

    def _parse_csv_list(self, s: str) -> List[str]:
        """解析CSV中的列表字段"""
        if not s:
            return []
        return [item.strip() for item in s.split('|') if item.strip()]

    def get_question(self, question_id: str) -> Optional[Question]:
        """根据ID获取题目"""
        return self._questions.get(question_id)

    def get_all_questions(self) -> List[Question]:
        """获取所有题目"""
        return list(self._questions.values())

    def filter_by_knowledge(self, knowledge_points: List[str],
                            exclude: bool = False) -> List[Question]:
        """按知识点筛选题目"""
        if not knowledge_points:
            return self.get_all_questions()

        result_ids = set()
        for kp in knowledge_points:
            if kp in self._by_knowledge:
                result_ids.update(self._by_knowledge[kp])

        if exclude:
            all_ids = set(self._questions.keys())
            result_ids = all_ids - result_ids

        return [self._questions[qid] for qid in result_ids]

    def filter_by_difficulty(self, difficulty: DifficultyLevel) -> List[Question]:
        """按难度筛选题目"""
        return [self._questions[qid]
                for qid in self._by_difficulty.get(difficulty, [])]

    def filter_by_type(self, question_type: QuestionType) -> List[Question]:
        """按题型筛选题目"""
        return [self._questions[qid]
                for qid in self._by_type.get(question_type, [])]

    def filter_by_tags(self, tags: List[str], match_all: bool = False) -> List[Question]:
        """按标签筛选题目"""
        if not tags:
            return self.get_all_questions()

        if match_all:
            result_ids = None
            for tag in tags:
                tag_ids = set(self._by_tag.get(tag, []))
                if result_ids is None:
                    result_ids = tag_ids
                else:
                    result_ids &= tag_ids
            if result_ids is None:
                return []
        else:
            result_ids = set()
            for tag in tags:
                result_ids.update(self._by_tag.get(tag, []))

        return [self._questions[qid] for qid in result_ids]

    def filter_complex(self,
                       knowledge_points: Optional[List[str]] = None,
                       exclude_knowledge: Optional[List[str]] = None,
                       difficulty: Optional[DifficultyLevel] = None,
                       question_type: Optional[QuestionType] = None,
                       tags: Optional[List[str]] = None) -> List[Question]:
        """复合条件筛选"""
        result = set(self._questions.keys())

        if knowledge_points:
            kp_ids = set()
            for kp in knowledge_points:
                kp_ids.update(self._by_knowledge.get(kp, []))
            result &= kp_ids

        if exclude_knowledge:
            exclude_ids = set()
            for kp in exclude_knowledge:
                exclude_ids.update(self._by_knowledge.get(kp, []))
            result -= exclude_ids

        if difficulty:
            result &= set(self._by_difficulty.get(difficulty, []))

        if question_type:
            result &= set(self._by_type.get(question_type, []))

        if tags:
            tag_ids = set()
            for tag in tags:
                tag_ids.update(self._by_tag.get(tag, []))
            result &= tag_ids

        return [self._questions[qid] for qid in result]

    def get_knowledge_points(self) -> List[str]:
        """获取所有知识点"""
        return sorted(self._by_knowledge.keys())

    def get_difficulty_distribution(self) -> Dict[str, int]:
        """获取难度分布统计"""
        return {k.value: len(v) for k, v in self._by_difficulty.items()}

    def get_type_distribution(self) -> Dict[str, int]:
        """获取题型分布统计"""
        return {k.value: len(v) for k, v in self._by_type.items()}

    def get_knowledge_distribution(self) -> Dict[str, int]:
        """获取知识点分布统计"""
        return {k: len(v) for k, v in self._by_knowledge.items()}

    def get_questions_by_knowledge_and_difficulty(
            self,
            knowledge_point: str,
            difficulty: DifficultyLevel) -> List[Question]:
        """按知识点和难度组合筛选"""
        kp_ids = set(self._by_knowledge.get(knowledge_point, []))
        diff_ids = set(self._by_difficulty.get(difficulty, []))
        return [self._questions[qid] for qid in (kp_ids & diff_ids)]

    def sample_questions(self,
                         questions: List[Question],
                         count: int,
                         seed: Optional[int] = None) -> List[Question]:
        """从题目列表中随机抽样"""
        import random
        if seed is not None:
            random.seed(seed)

        if count >= len(questions):
            return questions.copy()

        return random.sample(questions, count)

    def select_by_difficulty_ratio(
            self,
            questions: List[Question],
            total_count: int,
            difficulty_ratio: Dict[DifficultyLevel, float]) -> List[Question]:
        """按难度比例从题目列表中选题"""
        by_diff: Dict[DifficultyLevel, List[Question]] = defaultdict(list)
        for q in questions:
            by_diff[q.difficulty].append(q)

        result = []
        remaining = total_count
        diff_list = sorted(difficulty_ratio.keys(),
                           key=lambda x: difficulty_ratio[x],
                           reverse=True)

        for i, diff in enumerate(diff_list):
            ratio = difficulty_ratio[diff]
            if i == len(diff_list) - 1:
                count = remaining
            else:
                count = max(1, round(total_count * ratio))

            available = by_diff.get(diff, [])
            selected = self.sample_questions(available, min(count, len(available)))
            result.extend(selected)
            remaining -= len(selected)

            for q in selected:
                for d in by_diff:
                    if q in by_diff[d]:
                        by_diff[d].remove(q)

        if remaining > 0:
            all_remaining = [q for q in questions if q not in result]
            extra = self.sample_questions(all_remaining, min(remaining, len(all_remaining)))
            result.extend(extra)

        return result[:total_count]

    def select_by_knowledge_points(
            self,
            knowledge_points: Dict[str, int],
            difficulty_ratio: Optional[Dict[DifficultyLevel, float]] = None) -> List[Question]:
        """按知识点指定数量选题"""
        result = []

        for kp, count in knowledge_points.items():
            kp_questions = self.filter_by_knowledge([kp])
            if difficulty_ratio:
                selected = self.select_by_difficulty_ratio(
                    kp_questions, count, difficulty_ratio)
            else:
                selected = self.sample_questions(kp_questions, count)

            if len(selected) < count:
                raise ValueError(f"知识点 {kp} 只有 {len(selected)} 道题，需要 {count} 道")

            result.extend(selected)

        return result

    def __len__(self) -> int:
        return len(self._questions)

    def __contains__(self, question_id: str) -> bool:
        return question_id in self._questions
