"""
测试4项新功能
1. 选项乱序对齐验证
2. 试卷版本对照导出
3. 跨场次知识点掌握变化分析
4. 合并结果JSON/CSV导出
"""

import json
import sys
import os
sys.path.insert(0, os.getcwd())

from edu_exam_lib import (
    QuestionBank, ExamGenerator, ExamRule, Question,
    StudentAnswer, ExamGrader, ExamStatistics,
    ExamSystem, MergeResult
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
        import traceback
        traceback.print_exc()
        fail_count += 1

def test_shuffle_alignment():
    """测试1: 选项乱序对齐验证"""
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

    generator = ExamGenerator(bank)
    rule = ExamRule(
        total_questions=1,
        num_versions=3,
        shuffle_options=True,
        shuffle_questions=False,
        exam_title='对齐测试',
        difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
    )
    papers = generator.generate_exam(rule, seed=42)

    assert len(papers) == 3, "应该生成3份试卷"

    all_options = set()
    for paper in papers:
        q = paper.questions[0]
        options_str = str(q['options'])
        all_options.add(options_str)

    assert len(all_options) > 1, "不同版本的选项内容应该不同"

    for paper in papers:
        q = paper.questions[0]
        qid = q['question_id']

        correct_labels = paper.answer_key[qid]
        correct_content = [q['options'][label] for label in correct_labels]

        assert 'def' in correct_content, "正确答案内容应该是def"

        grader = ExamGrader(paper)
        answers = {qid: correct_labels}
        sa = StudentAnswer('S001', '测试', paper.paper_id, answers)
        result = grader.grade(sa)
        assert result.total_score == 10, "用卷面正确答案应该得满分"

        printable = generator.generate_printable_exam(paper)
        answer_key = generator.generate_answer_key(paper)
        answer_sheet = generator.generate_printable_answer_sheet(paper)

        assert isinstance(printable, str) and len(printable) > 0
        assert isinstance(answer_key, str) and len(answer_key) > 0
        assert isinstance(answer_sheet, str) and len(answer_sheet) > 0

def test_version_comparison():
    """测试2: 试卷版本对照导出"""
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

    generator = ExamGenerator(bank)
    rule = ExamRule(
        total_questions=2,
        num_versions=3,
        shuffle_options=True,
        shuffle_questions=True,
        exam_title='版本对照测试',
        difficulty_ratio={'easy': 0.5, 'medium': 0.5, 'hard': 0},
    )
    papers = generator.generate_exam(rule, seed=42)

    comparison = generator.generate_version_comparison(papers)
    assert isinstance(comparison, str) and len(comparison) > 0, "版本对照应该生成字符串"
    assert '多版本试卷对照表' in comparison, "应该包含标题"
    assert '版本A' in comparison or 'A版本' in comparison or 'A' in comparison, "应该包含版本A"
    assert '版本B' in comparison or 'B版本' in comparison or 'B' in comparison, "应该包含版本B"
    assert '正确答案' in comparison, "应该包含正确答案列"

    assert '选项映射对照表' in comparison, "应该包含选项映射对照表"
    assert '原选项' in comparison, "应该包含原选项列"

    assert '说明' in comparison, "应该包含说明部分"

    output_file = generator.export_version_comparison(papers, 'output', 'test_v2')
    assert os.path.exists(output_file), "应该导出文件"
    assert 'version_comparison' in output_file, "文件名应该包含version_comparison"

def test_knowledge_trend():
    """测试3: 跨场次知识点掌握变化分析"""
    system = ExamSystem()

    with open('sample_questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    system.import_questions(data['questions'])

    rule1 = ExamRule(
        total_questions=8,
        num_versions=1,
        exam_title='第一场',
        difficulty_ratio={'easy': 0.5, 'medium': 0.3, 'hard': 0.2},
    )
    paper1 = system.generate_exam(rule1, seed=1)[0]

    rule2 = ExamRule(
        total_questions=8,
        num_versions=1,
        exam_title='第二场',
        difficulty_ratio={'easy': 0.4, 'medium': 0.4, 'hard': 0.2},
    )
    paper2 = system.generate_exam(rule2, seed=2)[0]

    rule3 = ExamRule(
        total_questions=8,
        num_versions=1,
        exam_title='第三场',
        difficulty_ratio={'easy': 0.3, 'medium': 0.4, 'hard': 0.3},
    )
    paper3 = system.generate_exam(rule3, seed=3)[0]

    import random
    random.seed(123)

    all_papers = [paper1, paper2, paper3]
    all_results = []

    for paper in all_papers:
        qids = [q['question_id'] for q in paper.questions]
        answers_list = []
        for i in range(5):
            answers = {}
            for qid in qids:
                correct = paper.answer_key[qid]
                prob = 0.5 + i * 0.1
                if random.random() < prob:
                    answers[qid] = correct
                else:
                    answers[qid] = ['A'] if 'A' not in correct else ['B']
            answers_list.append({
                'student_id': f'S{i+1:03d}',
                'student_name': f'学生{i+1}',
                'paper_id': paper.paper_id,
                'answers': answers,
            })
        results = system.grade_exam(paper.paper_id, answers_list)
        all_results.append(results)

    from edu_exam_lib import ExamGrader
    merge_result = ExamGrader.merge_exam_results(all_results)

    assert hasattr(merge_result, 'get_knowledge_trend'), "应该有get_knowledge_trend方法"
    assert hasattr(merge_result, 'get_class_knowledge_trend'), "应该有get_class_knowledge_trend方法"

    student_trend = merge_result.get_knowledge_trend('S001')
    assert student_trend is not None, "应该能获取学生知识点趋势"
    assert 'knowledge_points' in student_trend, "应该包含knowledge_points"
    assert 'weak_points' in student_trend, "应该包含weak_points"
    assert 'student_name' in student_trend, "应该包含学生姓名"

    assert isinstance(student_trend['knowledge_points'], dict), "knowledge_points应该是字典"
    if student_trend['knowledge_points']:
        first_kp = list(student_trend['knowledge_points'].keys())[0]
        kp_info = student_trend['knowledge_points'][first_kp]
        assert 'avg_mastery' in kp_info, "应该有avg_mastery"
        assert 'trend' in kp_info, "应该有trend"
        assert 'is_weak' in kp_info, "应该有is_weak"
        assert 'mastery_history' in kp_info, "应该有mastery_history"

    class_trend = merge_result.get_class_knowledge_trend()
    assert 'knowledge_points' in class_trend, "应该包含knowledge_points"
    assert 'weak_points' in class_trend, "应该包含weak_points"
    assert 'total_knowledge_points' in class_trend, "应该有total_knowledge_points"

    student_report = merge_result.generate_knowledge_trend_report('S001')
    assert isinstance(student_report, str) and len(student_report) > 0
    assert '知识点掌握变化报告' in student_report

    class_report = merge_result.generate_knowledge_trend_report()
    assert isinstance(class_report, str) and len(class_report) > 0
    assert '全班知识点掌握变化报告' in class_report

def test_merge_export():
    """测试4: 合并结果JSON和CSV导出"""
    system = ExamSystem()

    with open('sample_questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    system.import_questions(data['questions'])

    rule1 = ExamRule(
        total_questions=5, num_versions=1, exam_title='测试1',
        difficulty_ratio={'easy': 0.6, 'medium': 0.4, 'hard': 0},
    )
    paper1 = system.generate_exam(rule1, seed=1)[0]

    rule2 = ExamRule(
        total_questions=5, num_versions=1, exam_title='测试2',
        difficulty_ratio={'easy': 0.4, 'medium': 0.4, 'hard': 0.2},
    )
    paper2 = system.generate_exam(rule2, seed=2)[0]

    import random
    random.seed(456)

    all_results = []
    for paper_idx, paper in enumerate([paper1, paper2], 1):
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
        if paper_idx == 2:
            answers_list.append({
                'student_id': 'S001',
                'student_name': '学生1',
                'paper_id': paper2.paper_id,
                'answers': {qid: paper2.answer_key[qid] for qid in qids},
            })
        results = system.grade_exam(paper.paper_id, answers_list)
        all_results.append(results)

    from edu_exam_lib import ExamGrader
    merge_result = ExamGrader.merge_exam_results(all_results)

    json_str = merge_result.export_to_json()
    assert isinstance(json_str, str) and len(json_str) > 0, "JSON导出应该返回字符串"

    json_data = json.loads(json_str)
    assert 'summary' in json_data, "JSON应该包含summary"
    assert 'ranking' in json_data, "JSON应该包含ranking"
    assert 'exam_info' in json_data, "JSON应该包含exam_info"
    assert 'duplicates' in json_data, "JSON应该包含duplicates"
    assert 'student_summary' in json_data, "JSON应该包含student_summary"

    assert json_data['summary']['total_exams'] == 2, "应该有2场考试"
    assert len(json_data['ranking']) == 4, "应该有4个学生的排名"

    for rank_info in json_data['ranking']:
        assert 'rank' in rank_info, "排名数据应该有rank"
        assert 'student_id' in rank_info, "排名数据应该有student_id"
        assert 'total_score' in rank_info, "排名数据应该有total_score"
        assert 'exam_scores' in rank_info, "排名数据应该有exam_scores"

    json_file = merge_result.export_to_json('output/test_merge.json')
    assert os.path.exists(json_file), "JSON文件应该存在"
    assert json_file.endswith('.json'), "文件名应该以.json结尾"

    csv_str = merge_result.export_to_csv()
    assert isinstance(csv_str, str) and len(csv_str) > 0, "CSV导出应该返回字符串"

    lines = csv_str.strip().split('\n')
    assert len(lines) >= 2, "CSV应该至少有表头和一行数据"

    header = lines[0].split(',')
    assert '排名' in header[0] or '排名' == header[0].strip('"'), "CSV表头应该包含排名"
    assert '学号' in header[1] or '学号' == header[1].strip('"'), "CSV表头应该包含学号"
    assert '姓名' in header[2] or '姓名' == header[2].strip('"'), "CSV表头应该包含姓名"

    csv_file = merge_result.export_to_csv('output/test_merge.csv')
    assert os.path.exists(csv_file), "CSV文件应该存在"
    assert csv_file.endswith('.csv'), "文件名应该以.csv结尾"

    dup_count = len(merge_result.duplicates)
    assert dup_count > 0, "应该检测到重复记录"

    json_data2 = json.loads(merge_result.export_to_json())
    assert json_data2['summary']['duplicate_count'] == dup_count, "JSON中重复记录数应该正确"

if __name__ == '__main__':
    print("=" * 70)
    print("测试4项新功能")
    print("=" * 70)
    print()

    run_test("测试1: 选项乱序对齐验证", test_shuffle_alignment)
    run_test("测试2: 试卷版本对照导出", test_version_comparison)
    run_test("测试3: 跨场次知识点掌握变化分析", test_knowledge_trend)
    run_test("测试4: 合并结果JSON和CSV导出", test_merge_export)

    print()
    print("=" * 70)
    print(f"测试结果: 通过 {pass_count}, 失败 {fail_count}")
    print("=" * 70)

    if fail_count > 0:
        sys.exit(1)
    else:
        print("\n所有测试通过!")
        sys.exit(0)
