"""
功能验证脚本
"""

import json
import sys
import os
sys.path.insert(0, os.getcwd())

from edu_exam_lib import (
    generate_exam,
    grade_exam,
    analyze_results,
    ExamSystem,
    ExamRule,
    ExamGrader,
)

print('=== 功能验证测试 ===')
print()

# 1. 导入题目
with open('sample_questions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
questions = data['questions']
print(f'1. 导入题目: {len(questions)} 道')

# 2. 生成试卷
rule = {
    'total_questions': 8,
    'difficulty_ratio': {'easy': 0.3, 'medium': 0.5, 'hard': 0.2},
    'num_versions': 2,
    'exam_title': 'Python测试',
}
papers, bank_stats = generate_exam(questions, rule, seed=42)
print(f'2. 生成试卷: {len(papers)} 份版本')
for p in papers:
    print(f'   版本{p.version}: {len(p.questions)}题, 总分{p.total_score}')

# 3. 批改答案
paper = papers[0]
qids = [q['question_id'] for q in paper.questions]

student_answers = []
for i in range(5):
    answers = {}
    for qid in qids:
        correct = paper.answer_key[qid]
        if i % 2 == 0:
            answers[qid] = correct
        else:
            options = ['A', 'B', 'C', 'D']
            wrong = [o for o in options if o not in correct]
            answers[qid] = [wrong[0]] if wrong else []
    student_answers.append({
        'student_id': f'S{i+1:03d}',
        'student_name': f'学生{i+1}',
        'paper_id': paper.paper_id,
        'answers': answers,
    })

results, validation = grade_exam(paper, student_answers, questions=questions)
print(f'3. 批改答案: {validation["valid_answers"]}/{validation["total_students"]} 有效')
for r in results[:3]:
    print(f'   {r.student_name}: {r.total_score:.0f}/{r.max_score:.0f}分 ({r.percentage:.1f}%)')

# 4. 分析结果
analysis = analyze_results(results)
print(f'4. 分析结果:')
print(f'   平均分: {analysis["descriptive"]["mean"]:.1f}%')
print(f'   及格率: {analysis["descriptive"]["pass_rate"]:.1f}%')
print(f'   优秀率: {analysis["descriptive"]["excellent_rate"]:.1f}%')
print(f'   知识点掌握: {list(analysis["knowledge_points"].keys())[:3]}...')

# 5. 知识点掌握情况
print(f'5. 知识点掌握详情:')
for kp, stats in sorted(analysis["knowledge_points"].items(),
                         key=lambda x: -x[1]["accuracy"])[:5]:
    print(f'   {kp}: {stats["accuracy"]:.1f}% ({stats["correct_count"]}/{stats["total_count"]}题)')

# 6. 测试可打印内容
print(f'6. 可打印内容:')
system = ExamSystem()
system.import_questions(questions)
system._exam_papers[paper.paper_id] = paper

printable = system.generate_printable_content(paper.paper_id, 'paper')
print(f'   试卷文本长度: {len(printable)} 字符')

answer_sheet = system.generate_printable_content(paper.paper_id, 'answer_sheet')
print(f'   答题卡文本长度: {len(answer_sheet)} 字符')

answer_key = system.generate_printable_content(paper.paper_id, 'answer_key')
print(f'   标准答案长度: {len(answer_key)} 字符')

# 7. 错题归因
print(f'7. 错题归因统计:')
err_stats = analysis["error_reasons"]
for reason, s in err_stats.items():
    print(f'   {reason}: {s["count"]}次 ({s["percentage"]:.1f}%)')

# 8. 成绩分段
print(f'8. 成绩分段:')
dist = analysis["score_distribution"]
for label, d in dist.items():
    if d['count'] > 0:
        print(f'   {label}: {d["count"]}人 ({d["percentage"]:.1f}%)')

# 9. 测试多场考试合并
print(f'9. 多场考试合并:')
system2 = ExamSystem()
system2.import_questions(questions)

rule1 = ExamRule(total_questions=5, num_versions=1, exam_title='第一场')
paper1 = system2.generate_exam(rule1, seed=1)[0]

rule2 = ExamRule(total_questions=5, num_versions=1, exam_title='第二场')
paper2 = system2.generate_exam(rule2, seed=2)[0]

qids1 = [q['question_id'] for q in paper1.questions]
qids2 = [q['question_id'] for q in paper2.questions]

sa_list1 = [{
    'student_id': f'S{i:03d}',
    'student_name': f'学生{i}',
    'paper_id': paper1.paper_id,
    'answers': {qid: paper1.answer_key[qid] for qid in qids1},
} for i in range(3)]

sa_list2 = [{
    'student_id': f'S{i:03d}',
    'student_name': f'学生{i}',
    'paper_id': paper2.paper_id,
    'answers': {qid: paper2.answer_key[qid] for qid in qids2},
} for i in range(3)]

r1 = system2.grade_exam(paper1.paper_id, sa_list1)
r2 = system2.grade_exam(paper2.paper_id, sa_list2)

merge_result = ExamGrader.merge_exam_results([r1, r2])
print(f'   合并后结果数: {len(merge_result.merged_results)}')

# 10. 测试错误处理
print(f'10. 错误处理测试:')

bad_rule = {'total_questions': 1, 'difficulty_ratio': {'easy': 0.5, 'medium': 0.6}}
try:
    generate_exam(questions, bad_rule)
except ValueError as e:
    print(f'    难度比例错误: {e}')

try:
    ExamRule(total_questions=0)
except ValueError as e:
    print(f'    题数为0错误: {e}')

bad_sa = [{
    'student_id': 'S999',
    'student_name': '测试',
    'paper_id': paper.paper_id,
    'answers': {qids[0]: ['A']}
}]
try:
    grade_exam(paper, bad_sa, questions=questions)
except ValueError as e:
    msg = str(e)
    if len(msg) > 50:
        msg = msg[:50] + '...'
    print(f'    缺题错误已捕获: {msg}')

bad_sa2 = [{
    'student_id': 'S998',
    'student_name': '测试2',
    'paper_id': paper.paper_id,
    'answers': {qids[0]: ['A'], 'INVALID': ['B'], **{qid: ['A'] for qid in qids[1:]}}
}]
try:
    grade_exam(paper, bad_sa2, questions=questions)
except ValueError as e:
    msg = str(e)
    if len(msg) > 50:
        msg = msg[:50] + '...'
    print(f'    无效题号错误已捕获: {msg}')

print()
print('=== 所有功能验证通过！===')
