"""
测试同题多卷模式
"""

import json
import sys
import os
sys.path.insert(0, os.getcwd())

from edu_exam_lib import (
    QuestionBank, ExamGenerator, ExamRule, Question
)

bank = QuestionBank()
bank.add_question(Question(
    question_id='Q001', content='题1',
    options=['A1', 'B1', 'C1', 'D1'],
    correct_answer=['A'],
    knowledge_points=['kp1'], difficulty='easy', score=10
))
bank.add_question(Question(
    question_id='Q002', content='题2',
    options=['A2', 'B2', 'C2', 'D2'],
    correct_answer=['A', 'B'],
    knowledge_points=['kp2'], difficulty='medium', score=10
))
bank.add_question(Question(
    question_id='Q003', content='题3',
    options=['A3', 'B3', 'C3', 'D3'],
    correct_answer=['C'],
    knowledge_points=['kp1'], difficulty='easy', score=10
))

generator = ExamGenerator(bank)
rule = ExamRule(
    total_questions=3,
    num_versions=3,
    shuffle_options=True,
    shuffle_questions=True,
    same_questions=True,
    exam_title='同题多卷测试',
    difficulty_ratio={'easy': 2/3, 'medium': 1/3, 'hard': 0},
)
papers = generator.generate_exam(rule, seed=42)

print("=" * 80)
print("同题多卷模式验证")
print("=" * 80)
print()

print(f"生成了 {len(papers)} 份试卷")
print()

all_qids = set()
for i, paper in enumerate(papers):
    qids = [q['question_id'] for q in paper.questions]
    all_qids.add(tuple(sorted(qids)))
    print(f"版本 {paper.version} 题目ID: {qids}")
    print(f"  显示题号: {[q['display_num'] for q in paper.questions]}")

print()
if len(all_qids) == 1:
    print("[OK] 所有版本的题目ID相同（同题多卷模式正确）")
else:
    print("[FAILED] 不同版本的题目ID不同（同题多卷模式有问题）")

print()
print("版本对照表预览:")
print("-" * 80)
comparison = generator.generate_version_comparison(papers)
for line in comparison.split('\n')[:60]:
    print(line)

print()
print("=" * 80)
print("验证完成")
print("=" * 80)
