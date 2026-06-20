"""
使用示例：教育测评系统类库
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from edu_exam_lib import (
    generate_exam,
    grade_exam,
    analyze_results,
    ExamSystem,
    ExamRule,
    StudentAnswer,
    ExamGrader,
    ExamStatistics,
)


def demo_simple_api():
    """演示简单API函数的使用"""
    print("=" * 70)
    print("演示1：使用简单API函数")
    print("=" * 70)
    print()

    with open('sample_questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    questions = data['questions']

    print(f"1. 导入题目: 共 {len(questions)} 道题")
    print()

    rule = {
        'total_questions': 10,
        'difficulty_ratio': {'easy': 0.3, 'medium': 0.5, 'hard': 0.2},
        'question_type_ratio': {'single_choice': 0.6, 'multiple_choice': 0.3, 'true_false': 0.1},
        'shuffle_options': True,
        'shuffle_questions': True,
        'num_versions': 2,
        'exam_title': 'Python基础知识测试',
        'exam_duration': 60,
    }

    print("2. 生成试卷...")
    papers, bank_stats = generate_exam(questions, rule, seed=42)
    print(f"   成功生成 {len(papers)} 份试卷")
    print(f"   题库统计: {bank_stats['total_questions']} 道题, "
          f"{len(bank_stats['knowledge_points'])} 个知识点")
    print()

    paper_a = papers[0]
    print(f"3. 试卷 {paper_a.version} 信息:")
    print(f"   试卷ID: {paper_a.paper_id}")
    print(f"   题目数: {len(paper_a.questions)}, 总分: {paper_a.total_score}")
    print()

    print("4. 试卷题目预览（前3题）:")
    for q in paper_a.questions[:3]:
        num = q['display_num']
        qtype = q['question_type']
        score = q['score']
        print(f"   {num}. ({qtype}, {score}分) {q['content'][:50]}...")
        for label in sorted(q['options'].keys()):
            print(f"      {label}. {q['options'][label][:40]}...")
    print()

    print("5. 标准答案预览:")
    for q in paper_a.questions[:5]:
        qid = q['question_id']
        num = q['display_num']
        ans = "".join(paper_a.answer_key[qid])
        print(f"   {num}. {ans}")
    print()

    question_ids = [q['question_id'] for q in paper_a.questions]
    student_answers = [
        {
            'student_id': 'S001',
            'student_name': '张三',
            'paper_id': paper_a.paper_id,
            'answers': {qid: [paper_a.answer_key[qid][0]] for qid in question_ids},
        },
        {
            'student_id': 'S002',
            'student_name': '李四',
            'paper_id': paper_a.paper_id,
            'answers': {qid: ['A'] for qid in question_ids},
        },
        {
            'student_id': 'S003',
            'student_name': '王五',
            'paper_id': paper_a.paper_id,
            'answers': {qid: paper_a.answer_key[qid] for qid in question_ids[:5]} |
                       {qid: ['B'] for qid in question_ids[5:]},
        },
    ]

    print("6. 批改学生答案...")
    results, validation = grade_exam(paper_a, student_answers, questions=questions)
    print(f"   有效答案: {validation['valid_answers']}/{validation['total_students']}")
    for r in results:
        print(f"   {r.student_name}: {r.total_score:.0f}/{r.max_score:.0f}分 "
              f"({r.percentage:.1f}%)")
    print()

    print("7. 分析考试结果...")
    analysis = analyze_results(results)
    print(analysis['report'])
    print()


def demo_exam_system():
    """演示ExamSystem类的使用"""
    print("=" * 70)
    print("演示2：使用ExamSystem类进行完整流程")
    print("=" * 70)
    print()

    system = ExamSystem()

    print("1. 从JSON文件导入题目...")
    count, errors = system.import_questions_from_file('sample_questions.json')
    print(f"   成功导入 {count} 道题")
    if errors:
        print(f"   错误: {errors}")
    print()

    print("2. 题库统计:")
    stats = system.get_bank_stats()
    print(f"   总题数: {stats['total_questions']}")
    print(f"   知识点: {stats['knowledge_points']}")
    print(f"   难度分布: {stats['difficulty_distribution']}")
    print(f"   题型分布: {stats['type_distribution']}")
    print()

    rule = ExamRule(
        total_questions=8,
        knowledge_points={'Python基础': 5, '函数定义': 2, '列表': 1},
        difficulty_ratio={'easy': 0.3, 'medium': 0.5, 'hard': 0.2},
        num_versions=1,
        exam_title='Python专项测试',
        exam_duration=45,
    )

    print("3. 按知识点指定数量组卷...")
    papers = system.generate_exam(rule, seed=123)
    paper = papers[0]
    print(f"   生成试卷: {paper.paper_id}, 版本{paper.version}")
    print(f"   题目数: {len(paper.questions)}, 总分: {paper.total_score}")
    print()

    print("4. 知识点分布:")
    kp_count = {}
    for q in paper.questions:
        for kp in q['knowledge_points']:
            kp_count[kp] = kp_count.get(kp, 0) + 1
    for kp, cnt in kp_count.items():
        print(f"   {kp}: {cnt} 题")
    print()

    print("5. 导出可打印的试卷文本...")
    printable = system.generate_printable_content(paper.paper_id, 'paper')
    with open('output/exam_paper.txt', 'w', encoding='utf-8') as f:
        f.write(printable)
    print("   已保存到 output/exam_paper.txt")
    print()

    answer_sheet = system.generate_printable_content(paper.paper_id, 'answer_sheet')
    with open('output/answer_sheet.txt', 'w', encoding='utf-8') as f:
        f.write(answer_sheet)
    print("   答题卡已保存到 output/answer_sheet.txt")
    print()

    answer_key = system.generate_printable_content(paper.paper_id, 'answer_key')
    with open('output/answer_key.txt', 'w', encoding='utf-8') as f:
        f.write(answer_key)
    print("   标准答案已保存到 output/answer_key.txt")
    print()

    print("6. 验证学生答案（错误演示）:")
    print("   6.1 字典格式 - 无效题号和缺失答案:")
    bad_answer_dict = {
        'student_id': 'S999',
        'student_name': '测试学生',
        'paper_id': paper.paper_id,
        'answers': {
            paper.questions[0]['question_id']: ['A'],
            'INVALID_ID': ['B'],
        }
    }
    is_valid, errors, missing = system.validate_student_answer(paper.paper_id, bad_answer_dict)
    print(f"      是否有效: {is_valid}")
    if errors:
        print(f"      错误: {errors}")
    if missing:
        print(f"      缺失: {missing}")

    print()
    print("   6.2 列表格式 - 重复题号检测:")
    qid1 = paper.questions[0]['question_id']
    qid2 = paper.questions[1]['question_id']
    bad_answer_list = {
        'student_id': 'S998',
        'student_name': '重复学生',
        'paper_id': paper.paper_id,
        'answers': [
            {'question_id': qid1, 'answer': 'A'},
            {'question_id': qid2, 'answer': 'B'},
            {'question_id': qid1, 'answer': 'C'},
            {'question_id': qid2, 'answer': 'D'},
        ]
    }
    is_valid2, errors2, missing2 = system.validate_student_answer(paper.paper_id, bad_answer_list)
    print(f"      是否有效: {is_valid2}")
    if errors2:
        print(f"      错误: {errors2}")
    if missing2:
        print(f"      缺失: {missing2}")

    print()
    print("   6.3 批改时重复题号报错:")
    try:
        result = system.grade_exam(paper.paper_id, [bad_answer_list])
        print(f"      批改成功 - 这不应该发生!")
    except ValueError as e:
        print(f"      批改报错（预期行为）:")
        print(f"      {e}")
    print()

    print("7. 批量导入学生答案并批改...")
    qids = [q['question_id'] for q in paper.questions]

    import random
    random.seed(456)

    student_names = ['赵一', '钱二', '孙三', '李四', '周五', '吴六', '郑七', '王八', '冯九', '陈十']
    student_answers = []
    for i, name in enumerate(student_names):
        answers = {}
        for qid in qids:
            correct = paper.answer_key[qid]
            if random.random() < 0.7:
                answers[qid] = correct
            else:
                options = ['A', 'B', 'C', 'D']
                wrong = [o for o in options if o not in correct]
                if wrong:
                    answers[qid] = [random.choice(wrong)]
                else:
                    answers[qid] = []

        student_answers.append({
            'student_id': f'S{i+1:03d}',
            'student_name': name,
            'paper_id': paper.paper_id,
            'answers': answers,
        })

    results = system.grade_exam(paper.paper_id, student_answers)
    print(f"   完成 {len(results)} 名学生的判分")
    print()

    print("8. 学生成绩排名:")
    analysis = system.analyze_results(paper.paper_id)
    ranks = analysis.rank_students()
    for r in ranks[:5]:
        print(f"   第{r['rank']}名: {r['student_name']} "
              f"{r['percentage']:.1f}% ({r['total_score']:.0f}分)")
    print("   ...")
    print()

    print("9. 生成第一名的成绩报告...")
    top_student = system.get_results(paper.paper_id)[0]
    report = system.generate_grade_report(top_student)
    with open('output/grade_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    print("   已保存到 output/grade_report.txt")
    print("   报告预览:")
    for line in report.split('\n')[:20]:
        print(f"   {line}")
    print()

    print("10. 生成班级统计报告...")
    stats_report = analysis.generate_statistics_report()
    with open('output/class_statistics.txt', 'w', encoding='utf-8') as f:
        f.write(stats_report)
    print("    已保存到 output/class_statistics.txt")
    print("    报告预览:")
    for line in stats_report.split('\n')[:30]:
        print(f"    {line}")
    print()


def demo_merge_results():
    """演示多场考试结果合并"""
    print("=" * 70)
    print("演示3：多场考试结果合并")
    print("=" * 70)
    print()

    system = ExamSystem()

    count, errors = system.import_questions_from_file('sample_questions.json')
    print(f"导入题目: {count} 道")
    print()

    rule1 = ExamRule(
        total_questions=5,
        num_versions=1,
        exam_title='第一次测验',
        difficulty_ratio={'easy': 0.6, 'medium': 0.4, 'hard': 0},
    )
    paper1 = system.generate_exam(rule1, seed=1)[0]
    print(f"生成试卷1: {paper1.paper_id} ({paper1.title})")

    rule2 = ExamRule(
        total_questions=5,
        num_versions=1,
        exam_title='第二次测验',
        difficulty_ratio={'easy': 0.4, 'medium': 0.4, 'hard': 0.2},
    )
    paper2 = system.generate_exam(rule2, seed=2)[0]
    print(f"生成试卷2: {paper2.paper_id} ({paper2.title})")
    print()

    import random
    random.seed(789)

    for paper_idx, paper in enumerate([paper1, paper2], 1):
        qids = [q['question_id'] for q in paper.questions]
        student_answers = []
        for i in range(5):
            answers = {}
            for qid in qids:
                correct = paper.answer_key[qid]
                if random.random() < 0.65:
                    answers[qid] = correct
                else:
                    answers[qid] = ['A'] if 'A' not in correct else ['B']

            student_answers.append({
                'student_id': f'S{i+1:03d}',
                'student_name': f'学生{i+1}',
                'paper_id': paper.paper_id,
                'answers': answers,
            })

        if paper_idx == 2:
            student_answers.append({
                'student_id': 'S001',
                'student_name': '学生1',
                'paper_id': paper2.paper_id,
                'answers': {qid: paper2.answer_key[qid] for qid in qids},
            })

        results = system.grade_exam(paper.paper_id, student_answers)
        print(f"场次{paper_idx} - 试卷 {paper.paper_id} 批改完成，共 {len(results)} 份结果")

    print()
    print("=" * 50)
    print("合并两场考试结果...")
    print("=" * 50)
    merge_result = system.merge_exam_results([paper1.paper_id, paper2.paper_id])

    print()
    print("1. 基础信息:")
    print(f"   合并后结果数: {len(merge_result.merged_results)}")
    print(f"   涉及学生数: {len(merge_result.student_summary)}")
    print(f"   合并场次: {len(merge_result.exam_info)} 场")

    print()
    print("2. 重复记录检测:")
    if merge_result.duplicates:
        print(f"   检测到重复记录: {len(merge_result.duplicates)} 条")
        for dup in merge_result.duplicates:
            print(f"   - {dup['student_name']}({dup['student_id']}) "
                  f"试卷{dup['paper_id']} 场次{dup['exam_index']} 得分{dup['score']}")
    else:
        print("   无重复记录")

    print()
    print("3. 错误信息:")
    if merge_result.errors:
        for err in merge_result.errors:
            print(f"   - {err}")
    else:
        print("   无错误")

    print()
    print("4. 学生汇总统计:")
    print("   " + "-" * 60)
    print(f"   {'学号':<8}{'姓名':<8}{'场次':<8}{'总分':<10}"
          f"{'平均分':<10}{'缺考':<8}")
    print("   " + "-" * 60)

    for summary in merge_result.get_all_students_summary()[:5]:
        missing = ",".join([str(x) for x in summary['missing_exams']]) if summary['missing_exams'] else "-"
        print(f"   {summary['student_id']:<8}{summary['student_name']:<8}"
              f"{summary['exam_count']:<8}"
              f"{summary['total_score']:<10.1f}{summary['avg_score']:<10.1f}"
              f"{missing:<8}")

    print()
    print("5. 各学生各场次成绩:")
    print("   " + "-" * 60)

    for summary in merge_result.get_all_students_summary()[:3]:
        print(f"   {summary['student_name']}({summary['student_id']}):")
        for exam_score in summary['exam_scores']:
            if exam_score['has_score']:
                status = "OK"
                score_str = f"{exam_score['score']}/{exam_score['max_score']} ({exam_score['percentage']}%)"
            else:
                status = "缺考"
                score_str = "0/0"
            print(f"     场次{exam_score['exam_index']}: {score_str} {status}")

    print()
    print("6. 跨场次汇总报告:")
    print("   " + "-" * 60)
    try:
        merged_stats = ExamStatistics(merge_result.merged_results, allow_multi_paper=True)
        desc = merged_stats.get_descriptive_stats()
        print(f"   总记录数: {desc['count']}")
        print(f"   平均分: {desc['mean']:.1f}%")
        print(f"   及格率: {desc['pass_rate']:.1f}%")
        print(f"   优秀率: {desc['excellent_rate']:.1f}%")
        print(f"   最高分: {desc['max']:.1f}%")
        print(f"   最低分: {desc['min']:.1f}%")
        print()

        multi_report = merged_stats.generate_multi_paper_report()
        for line in multi_report.split('\n')[:20]:
            print(f"   {line}")
    except Exception as e:
        print(f"   统计时出错: {e}")

    print()
    print("7. 生成合并汇总报告...")
    summary_report = merge_result.generate_summary_report()
    with open('output/merge_summary.txt', 'w', encoding='utf-8') as f:
        f.write(summary_report)
    print("   已保存到 output/merge_summary.txt")
    print()
    print("   报告预览:")
    for line in summary_report.split('\n')[:25]:
        print(f"   {line}")
    print()


def demo_csv_import():
    """演示CSV导入"""
    print("=" * 70)
    print("演示4：从CSV文件导入题库")
    print("=" * 70)
    print()

    system = ExamSystem()

    count, errors = system.import_questions_from_file('sample_questions.csv')
    print(f"成功导入 {count} 道题")
    if errors:
        print(f"错误: {errors}")
    print()

    stats = system.get_bank_stats()
    print("题库统计:")
    print(f"  总题数: {stats['total_questions']}")
    print(f"  难度分布: {stats['difficulty_distribution']}")
    print(f"  题型分布: {stats['type_distribution']}")
    print()

    rule = ExamRule(
        total_questions=8,
        num_versions=1,
        exam_title='CSV导入测试',
    )

    papers = system.generate_exam(rule, seed=999)
    paper = papers[0]
    print(f"生成试卷: {paper.paper_id}, {len(paper.questions)} 道题")
    print()

    print("题目预览:")
    for q in paper.questions[:5]:
        print(f"  {q['display_num']}. {q['content'][:60]}...")
    print()


if __name__ == '__main__':
    os.makedirs('output', exist_ok=True)

    demo_simple_api()
    print()
    print("按Enter继续下一个演示...")
    input()

    demo_exam_system()
    print()
    print("按Enter继续下一个演示...")
    input()

    demo_merge_results()
    print()
    print("按Enter继续下一个演示...")
    input()

    demo_csv_import()
    print()
    print("所有演示完成！")
