"""
测试重复题号检测功能
"""

import json
import sys
import os
sys.path.insert(0, os.getcwd())

from edu_exam_lib import QuestionBank, ExamGenerator, ExamRule, Question, StudentAnswer, ExamGrader

print("=" * 60)
print("测试1: 列表式答题记录中的重复题号")
print("=" * 60)

# 创建一个简单测试
bank = QuestionBank()
bank.add_question(Question(
    question_id='Q001',
    content='测试题1',
    options=['A', 'B', 'C', 'D'],
    correct_answer=['A'],
    knowledge_points=['test'],
    difficulty='easy',
    question_type='single_choice',
    score=10,
))
bank.add_question(Question(
    question_id='Q002',
    content='测试题2',
    options=['A', 'B', 'C', 'D'],
    correct_answer=['B'],
    knowledge_points=['test'],
    difficulty='easy',
    question_type='single_choice',
    score=10,
))

generator = ExamGenerator(bank)
rule = ExamRule(
    total_questions=2,
    num_versions=1,
    shuffle_options=False,
    shuffle_questions=False,
    exam_title='重复题号测试',
    difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
)
papers = generator.generate_exam(rule, seed=42)
paper = papers[0]

# 测试列表式答题记录（含重复题号）
list_answers_with_dup = [
    {'question_id': 'Q001', 'answer': 'A'},
    {'question_id': 'Q002', 'answer': 'B'},
    {'question_id': 'Q001', 'answer': 'C'},  # Q001重复了
]

print("\n学生答案列表（含重复Q001）:")
for entry in list_answers_with_dup:
    print(f"  {entry}")

sa = StudentAnswer('S001', '测试学生', paper.paper_id, list_answers_with_dup)

print(f"\nhas_duplicates: {sa.has_duplicates}")
print(f"duplicate_question_ids: {sa.duplicate_question_ids}")
print(f"答案字典（最后一个覆盖）: {sa.answers}")

# 验证
is_valid, errors, missing = sa.validate(paper)
print(f"\nvalidate 结果:")
print(f"  is_valid: {is_valid}")
print(f"  errors: {errors}")
print(f"  missing: {missing}")

# 批改时应该报错
print("\n" + "=" * 60)
print("测试2: 批改时重复题号报错")
print("=" * 60)

grader = ExamGrader(paper)
try:
    result = grader.grade(sa)
    print(f"  批改成功 - 这不应该发生!")
except ValueError as e:
    print(f"  批改报错（预期行为）:")
    print(f"    {e}")

print("\n" + "=" * 60)
print("测试3: 无重复的正常答案")
print("=" * 60)

# 正常答案
normal_answers = [
    {'question_id': 'Q001', 'answer': 'A'},
    {'question_id': 'Q002', 'answer': 'B'},
]

sa2 = StudentAnswer('S002', '正常学生', paper.paper_id, normal_answers)
print(f"has_duplicates: {sa2.has_duplicates}")
print(f"duplicate_question_ids: {sa2.duplicate_question_ids}")

is_valid2, errors2, missing2 = sa2.validate(paper)
print(f"validate: is_valid={is_valid2}, errors={errors2}, missing={missing2}")

try:
    result2 = grader.grade(sa2)
    print(f"批改成功，得分: {result2.total_score}/{result2.max_score}")
except ValueError as e:
    print(f"批改报错（不应该发生）: {e}")

print("\n" + "=" * 60)
print("测试4: 多个重复题号")
print("=" * 60)

multi_dup = [
    {'question_id': 'Q001', 'answer': 'A'},
    {'question_id': 'Q001', 'answer': 'B'},
    {'question_id': 'Q002', 'answer': 'C'},
    {'question_id': 'Q002', 'answer': 'D'},
    {'question_id': 'Q002', 'answer': 'A'},
]

sa3 = StudentAnswer('S003', '多重复', paper.paper_id, multi_dup)
print(f"has_duplicates: {sa3.has_duplicates}")
print(f"duplicate_question_ids: {sa3.duplicate_question_ids}")
print(f"_question_id_counts: {sa3._question_id_counts}")

is_valid3, errors3, missing3 = sa3.validate(paper)
print(f"validate errors: {errors3}")

print("\n" + "=" * 60)
print("测试5: 字典式答案（无重复检测）")
print("=" * 60)

dict_answers = {'Q001': 'A', 'Q002': 'B'}
sa4 = StudentAnswer('S004', '字典学生', paper.paper_id, dict_answers)
print(f"has_duplicates: {sa4.has_duplicates}")
print(f"duplicate_question_ids: {sa4.duplicate_question_ids}")

print("\n" + "=" * 60)
print("测试6: 列表式支持多种key名称")
print("=" * 60)

varied_keys = [
    {'qid': 'Q001', 'answer': 'A'},
    {'question_id': 'Q002', 'ans': 'B'},
    {'qid': 'Q001', 'answers': ['C']},
]

sa5 = StudentAnswer('S005', '多格式', paper.paper_id, varied_keys)
print(f"has_duplicates: {sa5.has_duplicates}")
print(f"duplicate_question_ids: {sa5.duplicate_question_ids}")
print(f"answers: {sa5.answers}")

print("\n" + "=" * 60)
print("OK 所有重复题号检测测试完成!")
print("=" * 60)
