"""
综合测试脚本 - 验证所有4项修复
"""

import json
import sys
import os
sys.path.insert(0, os.getcwd())

from edu_exam_lib import (
    QuestionBank, ExamGenerator, ExamRule, Question,
    StudentAnswer, ExamGrader, ExamStatistics,
    ExamSystem, generate_exam, grade_exam, analyze_results
)

pass_count = 0
fail_count = 0

def run_test(name, test_func):
    global pass_count, fail_count
    try:
        test_func()
        print(f"[OK] {name}")
        pass_count += 1
    except AssertionError as e:
        print(f"[FAILED] {name}: {e}")
        fail_count += 1
    except Exception as e:
        print(f"[FAILED] {name}: 异常 - {type(e).__name__}: {e}")
        fail_count += 1

def test_shuffle_between_versions():
    """测试1: 选项乱序在不同版本间正确性"""
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
        content='以下哪些是Python内置类型？',
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
        exam_title='测试乱序',
        difficulty_ratio={'easy': 0.5, 'medium': 0.5, 'hard': 0},
    )
    papers = generator.generate_exam(rule, seed=42)

    assert len(papers) == 3, "应该生成3份试卷"

    options_by_version = {}
    answers_by_version = {}
    for paper in papers:
        q = next(q for q in paper.questions if q['question_id'] == 'Q001')
        options_by_version[paper.version] = str(q['options'])
        answers_by_version[paper.version] = str(paper.answer_key['Q001'])

    unique_options = set(options_by_version.values())
    assert len(unique_options) > 1, f"不同版本的选项应该不同，但实际是: {options_by_version}"

    unique_answers = set(answers_by_version.values())
    assert len(unique_answers) > 1, f"不同版本的答案应该不同，但实际是: {answers_by_version}"

    for paper in papers:
        grader = ExamGrader(paper)
        qids = [q['question_id'] for q in paper.questions]
        correct_answers = {qid: paper.answer_key[qid] for qid in qids}
        sa = StudentAnswer('S001', '测试', paper.paper_id, correct_answers)
        result = grader.grade(sa)
        assert result.total_score == result.max_score, f"版本{paper.version}用正确答案应该得满分"

    printable = generator.generate_printable_exam(papers[0])
    answer_key = generator.generate_answer_key(papers[0])
    assert isinstance(printable, str) and len(printable) > 0, "打印试卷应该生成字符串"
    assert isinstance(answer_key, str) and len(answer_key) > 0, "标准答案应该生成字符串"

def test_duplicate_detection():
    """测试2: 重复题号检测"""
    bank = QuestionBank()
    bank.add_question(Question(
        question_id='Q001', content='测试1',
        options=['A', 'B', 'C', 'D'], correct_answer=['A'],
        knowledge_points=['test'], difficulty='easy', score=10
    ))
    bank.add_question(Question(
        question_id='Q002', content='测试2',
        options=['A', 'B', 'C', 'D'], correct_answer=['B'],
        knowledge_points=['test'], difficulty='easy', score=10
    ))

    generator = ExamGenerator(bank)
    rule = ExamRule(
        total_questions=2, num_versions=1,
        exam_title='重复测试',
        difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
    )
    paper = generator.generate_exam(rule, seed=1)[0]

    list_answers = [
        {'question_id': 'Q001', 'answer': 'A'},
        {'question_id': 'Q002', 'answer': 'B'},
        {'question_id': 'Q001', 'answer': 'C'},
    ]
    sa = StudentAnswer('S001', '测试', paper.paper_id, list_answers)

    assert sa.has_duplicates == True, "应该检测到重复"
    assert 'Q001' in sa.duplicate_question_ids, "Q001应该在重复列表中"

    is_valid, errors, missing = sa.validate(paper)
    assert is_valid == False, "有重复题号应该无效"
    assert any('Q001' in err and '2次' in err for err in errors), "错误信息应该包含Q001和次数"

    grader = ExamGrader(paper)
    try:
        grader.grade(sa)
        assert False, "有重复题号应该抛出异常"
    except ValueError as e:
        assert '重复' in str(e), "异常信息应该包含'重复'"
        assert 'Q001' in str(e), "异常信息应该包含重复的题号"

    normal_answers = [
        {'question_id': 'Q001', 'answer': 'A'},
        {'question_id': 'Q002', 'answer': 'B'},
    ]
    sa_normal = StudentAnswer('S002', '正常', paper.paper_id, normal_answers)
    assert sa_normal.has_duplicates == False, "无重复应该返回False"

    result = grader.grade(sa_normal)
    assert result.total_score == 20, "正常答案应该得满分"

    varied_keys = [
        {'qid': 'Q001', 'ans': 'A'},
        {'question_id': 'Q002', 'answers': ['B']},
    ]
    sa_varied = StudentAnswer('S003', '多格式', paper.paper_id, varied_keys)
    assert sa_varied.has_duplicates == False, "不同key格式应该也能正确解析"
    assert sa_varied.answers['Q001'] == ['A'], "qid和ans键应该能正确解析"

def test_multi_paper_merge():
    """测试3: 多场考试合并与跨场次汇总"""
    system = ExamSystem()

    with open('sample_questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    system.import_questions(data['questions'])

    rule1 = ExamRule(
        total_questions=5, num_versions=1,
        exam_title='第一场',
        difficulty_ratio={'easy': 0.6, 'medium': 0.4, 'hard': 0},
    )
    paper1 = system.generate_exam(rule1, seed=1)[0]

    rule2 = ExamRule(
        total_questions=5, num_versions=1,
        exam_title='第二场',
        difficulty_ratio={'easy': 0.4, 'medium': 0.4, 'hard': 0.2},
    )
    paper2 = system.generate_exam(rule2, seed=2)[0]

    import random
    random.seed(456)

    for paper in [paper1, paper2]:
        qids = [q['question_id'] for q in paper.questions]
        answers_list = []
        for i in range(4):
            answers = {}
            for qid in qids:
                correct = paper.answer_key[qid]
                if random.random() < 0.7:
                    answers[qid] = correct
                else:
                    answers[qid] = ['A'] if 'A' not in correct else ['B']
            answers_list.append({
                'student_id': f'S{i+1:03d}',
                'student_name': f'学生{i+1}',
                'paper_id': paper.paper_id,
                'answers': answers,
            })
        if paper == paper2:
            answers_list.append({
                'student_id': 'S001',
                'student_name': '学生1',
                'paper_id': paper2.paper_id,
                'answers': {qid: paper2.answer_key[qid] for qid in qids},
            })

        system.grade_exam(paper.paper_id, answers_list)

    merge_result = system.merge_exam_results([paper1.paper_id, paper2.paper_id])

    assert hasattr(merge_result, 'student_summary'), "MergeResult应该有student_summary"
    assert hasattr(merge_result, 'exam_info'), "MergeResult应该有exam_info"
    assert len(merge_result.student_summary) == 4, "应该有4个学生"
    assert len(merge_result.exam_info) == 2, "应该有2场考试信息"

    assert len(merge_result.duplicates) == 2, "应该检测到2条重复记录（S001在paper2有2条记录）"
    assert any(dup['student_id'] == 'S001' for dup in merge_result.duplicates), "应该有S001的重复记录"

    all_summary = merge_result.get_all_students_summary()
    assert len(all_summary) == 4, "应该有4个学生的汇总"

    for s in all_summary:
        assert 'total_score' in s, "应该有总分"
        assert 'avg_score' in s, "应该有平均分"
        assert 'exam_count' in s, "应该有参考场次数"
        assert 'missing_exams' in s, "应该有缺考场次"
        assert 'exam_scores' in s, "应该有各场次成绩列表"
        assert len(s['exam_scores']) == 2, "每个学生应该有2场考试的信息"

    s001 = merge_result.get_student_summary('S001')
    assert s001 is not None, "应该能获取S001的汇总"
    assert s001['exam_count'] == 2, "S001应该参加了2场考试"
    assert len(s001['missing_exams']) == 0, "S001没有缺考"

    s004 = merge_result.get_student_summary('S004')
    assert s004 is not None, "应该能获取S004的汇总"

    summary_report = merge_result.generate_summary_report()
    assert isinstance(summary_report, str) and len(summary_report) > 0, "应该生成汇总报告"
    assert '学生1' in summary_report, "报告应该包含学生姓名"
    assert 'S001' in summary_report, "报告应该包含学号"

    stats = ExamStatistics(merge_result.merged_results, allow_multi_paper=True)
    assert stats.is_multi_paper == True, "应该识别为跨试卷"
    assert len(stats.paper_ids) == 2, "应该有2份试卷"

    multi_summary = stats.get_multi_paper_summary()
    assert 'paper_info' in multi_summary, "应该有各场次信息"
    assert 'student_summary' in multi_summary, "应该有学生汇总"

    multi_report = stats.generate_multi_paper_report()
    assert isinstance(multi_report, str) and len(multi_report) > 0, "应该生成跨试卷报告"

    try:
        stats2 = ExamStatistics(merge_result.merged_results, allow_multi_paper=False)
        assert False, "不允许跨试卷时应该抛出异常"
    except ValueError as e:
        assert '不同试卷' in str(e), "异常应该说明是不同试卷"

def test_merge_demo_runs():
    """测试4: 示例脚本中的合并演示能完整运行"""
    system = ExamSystem()

    with open('sample_questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    count, errors = system.import_questions(data['questions'])
    assert count > 0, "应该导入成功"

    rule1 = ExamRule(
        total_questions=5, num_versions=1,
        exam_title='测验1',
        difficulty_ratio={'easy': 0.6, 'medium': 0.4, 'hard': 0},
    )
    paper1 = system.generate_exam(rule1, seed=1)[0]

    rule2 = ExamRule(
        total_questions=5, num_versions=1,
        exam_title='测验2',
        difficulty_ratio={'easy': 0.4, 'medium': 0.4, 'hard': 0.2},
    )
    paper2 = system.generate_exam(rule2, seed=2)[0]

    import random
    random.seed(789)

    for paper_idx, paper in enumerate([paper1, paper2], 1):
        qids = [q['question_id'] for q in paper.questions]
        answers_list = []
        for i in range(5):
            answers = {}
            for qid in qids:
                correct = paper.answer_key[qid]
                if random.random() < 0.65:
                    answers[qid] = correct
                else:
                    answers[qid] = ['A'] if 'A' not in correct else ['B']
            answers_list.append({
                'student_id': f'S{i+1:03d}',
                'student_name': f'学生{i+1}',
                'paper_id': paper.paper_id,
                'answers': answers,
            })
        if paper_idx == 2:
            answers_list.append({
                'student_id': 'S001',
                'student_name': '学生1',
                'paper_id': paper2.paper_id,
                'answers': {qid: paper2.answer_key[qid] for qid in qids},
            })
        system.grade_exam(paper.paper_id, answers_list)

    merge_result = system.merge_exam_results([paper1.paper_id, paper2.paper_id])

    assert merge_result is not None, "合并结果不应该为None"
    assert len(merge_result.merged_results) > 0, "合并结果应该有数据"
    assert len(merge_result.duplicates) > 0, "应该检测到重复记录"

    summary = merge_result.generate_summary_report()
    assert isinstance(summary, str), "汇总报告应该是字符串"
    assert '重复记录' in summary, "报告应该提到重复记录"
    assert '总分' in summary, "报告应该有总分"
    assert '平均分' in summary, "报告应该有平均分"

    try:
        merged_stats = ExamStatistics(merge_result.merged_results, allow_multi_paper=True)
        desc = merged_stats.get_descriptive_stats()
        assert 'mean' in desc, "应该有平均分统计"
        assert 'pass_rate' in desc, "应该有及格率"
    except Exception as e:
        assert False, f"跨试卷统计不应该出错: {e}"

if __name__ == '__main__':
    print("=" * 70)
    print("综合测试 - 验证所有4项修改")
    print("=" * 70)
    print()

    run_test("测试1: 选项乱序在不同版本间正确性", test_shuffle_between_versions)
    run_test("测试2: 重复题号检测（列表式、多种key格式）", test_duplicate_detection)
    run_test("测试3: 多场考试合并与跨场次汇总", test_multi_paper_merge)
    run_test("测试4: 示例脚本合并演示完整性", test_merge_demo_runs)

    print()
    print("=" * 70)
    print(f"测试结果: 通过 {pass_count}, 失败 {fail_count}")
    print("=" * 70)

    if fail_count > 0:
        sys.exit(1)
    else:
        print("\n所有测试通过!")
        sys.exit(0)
