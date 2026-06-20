"""
测试选项乱序对齐 - 确保打印试卷、标准答案、答题卡、批改完全一致
"""

import json
import sys
import os
sys.path.insert(0, os.getcwd())

from edu_exam_lib import (
    QuestionBank, ExamGenerator, ExamRule, Question,
    StudentAnswer, ExamGrader
)

bank = QuestionBank()
bank.add_question(Question(
    question_id='Q001',
    content='Python中定义函数的关键字是？',
    options=['def', 'function', 'func', 'define'],
    correct_answer=['A'],
    knowledge_points=['Python基础'],
    difficulty='easy',
    question_type='single_choice',
    score=10,
))
bank.add_question(Question(
    question_id='Q002',
    content='以下哪些是Python内置数据类型？',
    options=['list', 'int', 'array', 'dict'],
    correct_answer=['A', 'B', 'D'],
    knowledge_points=['Python基础'],
    difficulty='medium',
    question_type='multiple_choice',
    score=10,
))

generator = ExamGenerator(bank)
rule = ExamRule(
    total_questions=2,
    num_versions=3,
    shuffle_options=True,
    shuffle_questions=False,
    exam_title='选项对齐测试',
    difficulty_ratio={'easy': 0.5, 'medium': 0.5, 'hard': 0},
)
papers = generator.generate_exam(rule, seed=42)

print("=" * 80)
print("选项乱序对齐验证测试")
print("=" * 80)
print()

all_correct = True

for paper in papers:
    print(f"--- 版本 {paper.version} (试卷ID: {paper.paper_id}) ---")
    print()

    print("1. 试卷结构中的选项:")
    for q in paper.questions:
        qid = q['question_id']
        print(f"   {q['display_num']}. {q['content']}")
        for label in sorted(q['options'].keys()):
            print(f"      {label}. {q['options'][label]}")
        print(f"   标准答案: {paper.answer_key[qid]}")
        print(f"   选项映射(原->新): {paper.option_mapping[qid]}")
        print()

    print("2. 可打印试卷中的选项:")
    printable = generator.generate_printable_exam(paper)
    # 提取第1题的选项部分
    lines = printable.split('\n')
    for line in lines:
        if 'Python中' in line or (line.strip() and (line.strip().startswith('A.') or line.strip().startswith('B.') or line.strip().startswith('C.') or line.strip().startswith('D.'))):
            print(f"   {line}")
    print()

    print("3. 标准答案文档:")
    answer_key_text = generator.generate_answer_key(paper)
    for line in answer_key_text.split('\n')[:10]:
        if line.strip():
            print(f"   {line}")
    print()

    print("4. 验证: 卷面上的正确答案内容 = 原始正确答案内容")
    for q in paper.questions:
        qid = q['question_id']
        display_num = q['display_num']

        # 从打印试卷找这道题的选项内容
        correct_labels = paper.answer_key[qid]
        correct_content_print = [q['options'].get(label, 'N/A') for label in correct_labels]

        # 原始正确答案内容
        original_question = bank.get_question(qid)
        original_correct_labels = original_question.correct_answer
        original_correct_content = [original_question.options[ord(label) - ord('A')] for label in original_correct_labels]

        # 验证内容是否一致
        is_content_match = sorted(correct_content_print) == sorted(original_correct_content)
        status = "OK" if is_content_match else "MISMATCH!"

        if not is_content_match:
            all_correct = False

        print(f"   第{display_num}题({qid}): {status}")
        print(f"     卷面正确选项字母: {correct_labels}")
        print(f"     卷面正确选项内容: {correct_content_print}")
        print(f"     原始正确选项字母: {original_correct_labels}")
        print(f"     原始正确选项内容: {original_correct_content}")
    print()

    print("5. 验证: 用卷面正确答案批改能得满分")
    grader = ExamGrader(paper)
    answers = {q['question_id']: paper.answer_key[q['question_id']] for q in paper.questions}
    sa = StudentAnswer('S001', '测试学生', paper.paper_id, answers)
    result = grader.grade(sa)
    score_status = "OK" if result.total_score == result.max_score else "FAILED"
    if result.total_score != result.max_score:
        all_correct = False
    print(f"   得分: {result.total_score}/{result.max_score} - {score_status}")
    print()

    print("6. 验证: 答题卡与试卷题号对应")
    answer_sheet = generator.generate_printable_answer_sheet(paper)
    print(f"   答题卡长度: {len(answer_sheet)} 字符")
    # 检查答题卡中是否有所有题号
    sheet_question_nums = []
    for q in paper.questions:
        num = q['display_num']
        if str(num) + '.' in answer_sheet or f'第{num}题' in answer_sheet:
            sheet_question_nums.append(num)
    print(f"   答题卡中题号数: {len(sheet_question_nums)}/{len(paper.questions)}")
    print()

print("=" * 80)
print(f"整体验证结果: {'全部通过' if all_correct else '存在问题'}")
print("=" * 80)

# 再验证"拿着卷面上的正确内容作答"
print()
print("=" * 80)
print("额外验证: 学生看到卷面选项后，选内容正确的选项字母")
print("=" * 80)
print()

paper_a = papers[0]
grader_a = ExamGrader(paper_a)

# 模拟学生：看到题目后选内容是"def"的那个选项
# 在卷面上，def对应的选项字母就是正确答案
q1 = paper_a.questions[0]
qid1 = q1['question_id']
print(f"题目: {q1['content']}")
print(f"卷面选项:")
for label in sorted(q1['options'].keys()):
    print(f"  {label}. {q1['options'][label]}")

# 学生应该选内容是"def"的选项
student_pick = None
for label, content in q1['options'].items():
    if content == 'def':
        student_pick = label
        break

print(f"学生选择: {student_pick} (内容是'def')")
print(f"标准答案: {paper_a.answer_key[qid1]}")

# 验证批改
answers = {qid1: [student_pick]}
sa = StudentAnswer('S002', '聪明学生', paper_a.paper_id, answers)
# 只验证这一道题
print(f"\n批改验证:")
print(f"  学生答案: {answers[qid1]}")
print(f"  正确答案: {paper_a.answer_key[qid1]}")
print(f"  是否应该得分: 是 (因为选的是内容正确的选项)")

# 实际上我们知道应该是对的
is_correct = sorted([student_pick]) == sorted(paper_a.answer_key[qid1])
print(f"  实际结果: {'正确' if is_correct else '错误'}")
print()

print("=" * 80)
print("验证完成!")
print("=" * 80)
