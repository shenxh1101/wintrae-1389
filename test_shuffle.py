"""
测试选项乱序在不同版本间的正确性
"""

import json
import sys
import os
sys.path.insert(0, os.getcwd())

from edu_exam_lib import QuestionBank, ExamGenerator, ExamRule, Question, StudentAnswer, ExamGrader

# 验证不同版本的选项乱序
with open('sample_questions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
questions = [q for q in data['questions'] if q['question_id'] in ['Q001', 'Q002']]

bank = QuestionBank()
for q_data in questions:
    bank.add_question(Question.from_dict(q_data))

print('题库中的原始题目:')
for q in bank.get_all_questions():
    print(f'  {q.question_id}: {q.content}')
    print(f'    原始选项: {dict(zip(["A","B","C","D"], q.options))}')
    print(f'    原始答案: {q.correct_answer}')
    print()

generator = ExamGenerator(bank)
rule = ExamRule(
    total_questions=2,
    num_versions=3,
    shuffle_options=True,
    shuffle_questions=False,
    exam_title='测试乱序',
    difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
)

papers = generator.generate_exam(rule, seed=42)

print('=' * 60)
for paper in papers:
    print(f'版本 {paper.version} (试卷ID: {paper.paper_id}):')
    for q in paper.questions:
        qid = q['question_id']
        print(f'  {q["display_num"]}. {qid}: {q["content"][:30]}...')
        print(f'    选项: {q["options"]}')
        print(f'    标准答案: {paper.answer_key[qid]}')
        print(f'    选项映射(原始->新版): {paper.option_mapping[qid]}')
    print()

# 验证同一道题在不同版本中的选项是否不同
qid = 'Q001'
print('=' * 60)
print(f'题目 {qid} 在不同版本中的对比:')
options_by_version = {}
answers_by_version = {}
for paper in papers:
    q = next(q for q in paper.questions if q['question_id'] == qid)
    options_by_version[paper.version] = str(q['options'])
    answers_by_version[paper.version] = str(paper.answer_key[qid])
    print(f'  版本{paper.version}: 选项={q["options"]}, 答案={paper.answer_key[qid]}')

unique_options = set(options_by_version.values())
if len(unique_options) > 1:
    print(f'✅ 选项在不同版本中确实不同 ({len(unique_options)} 种不同排列)')
else:
    print(f'❌ 警告: 选项在不同版本中相同!')

# 验证批改是否使用正确版本的答案
print()
print('=' * 60)
print('验证批改使用正确版本的答案:')

for paper in papers[:2]:
    print(f'试卷 {paper.version}:')
    grader = ExamGrader(paper)
    qids = [q['question_id'] for q in paper.questions]
    
    answers_v1 = {qid: papers[0].answer_key[qid] for qid in qids}
    sa = StudentAnswer('S001', '测试学生', paper.paper_id, answers_v1)
    result = grader.grade(sa)
    if paper.version == 'A':
        expected = result.max_score
    else:
        expected = 0
    status = '✅ 正确' if result.total_score == expected else '❌ 错误'
    print(f'  用版本A答案批改版本{paper.version}: 得分={result.total_score}/{result.max_score} {status}')

# 验证打印试卷与答案是否一致
print()
print('=' * 60)
print('验证打印试卷与答案是否一致:')

paper = papers[0]
printable = generator.generate_printable_exam(paper)
answer_key = generator.generate_answer_key(paper)
answer_sheet = generator.generate_printable_answer_sheet(paper)

print(f'  可打印试卷: {len(printable)} 字符')
print(f'  标准答案: {len(answer_key)} 字符')
print(f'  答题卡: {len(answer_sheet)} 字符')

# 检查打印试卷中的选项与答案是否匹配
q = paper.questions[0]
qid = q['question_id']
display_num = q['display_num']
correct_ans = "".join(paper.answer_key[qid])
print(f'  第{display_num}题打印选项: {q["options"]}')
print(f'  第{display_num}题正确答案: {correct_ans}')
print(f'  答案对应选项内容: {q["options"].get(correct_ans[0], "N/A")}')

print()
print('=' * 60)
print('✅ 选项乱序验证完成')
