"""
综合测试 - 验证所有4项新功能
1. 同题多卷模式
2. 学生成长档案（知识点趋势）
3. 重复提交处理策略
4. 知识点趋势准确性验证
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

def test_same_questions_mode():
    """测试1: 同题多卷模式"""
    bank = QuestionBank()
    for i in range(5):
        bank.add_question(Question(
            question_id=f'Q{i+1:03d}',
            content=f'题目{i+1}',
            options=[f'A{i+1}', f'B{i+1}', f'C{i+1}', f'D{i+1}'],
            correct_answer=['A'],
            knowledge_points=[f'kp{i%3+1}'],
            difficulty='easy',
            score=10,
        ))

    generator = ExamGenerator(bank)
    rule = ExamRule(
        total_questions=5,
        num_versions=3,
        shuffle_options=True,
        shuffle_questions=True,
        same_questions=True,
        exam_title='同题多卷测试',
        difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
    )
    papers = generator.generate_exam(rule, seed=42)

    assert len(papers) == 3, "应该生成3份试卷"

    all_qid_sets = []
    for paper in papers:
        qids = sorted([q['question_id'] for q in paper.questions])
        all_qid_sets.append(tuple(qids))

    assert len(set(all_qid_sets)) == 1, f"所有版本应该有相同的题目ID，但有 {len(set(all_qid_sets))} 种不同组合"

    display_orders = []
    for paper in papers:
        order = [q['question_id'] for q in paper.questions]
        display_orders.append(order)

    assert display_orders[0] != display_orders[1] or display_orders[1] != display_orders[2], \
        "题号顺序应该在不同版本间有变化"

    comparison = generator.generate_version_comparison(papers)
    assert isinstance(comparison, str) and len(comparison) > 0
    assert '多版本试卷对照表' in comparison
    assert '选项映射对照表' in comparison
    assert '原选项' in comparison

    os.makedirs('output', exist_ok=True)
    out_file = generator.export_version_comparison(papers, 'output', 'v2_test')
    assert os.path.exists(out_file), "版本对照文件应该存在"

def test_student_growth_profile():
    """测试2: 学生成长档案（知识点趋势）"""
    system = ExamSystem()

    with open('sample_questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    system.import_questions(data['questions'])

    all_papers = []
    all_results = []

    import random
    random.seed(777)

    for exam_idx in range(3):
        rule = ExamRule(
            total_questions=8,
            num_versions=1,
            exam_title=f'第{exam_idx+1}场考试',
            difficulty_ratio={'easy': 0.5, 'medium': 0.3, 'hard': 0.2},
        )
        paper = system.generate_exam(rule, seed=100+exam_idx)[0]
        all_papers.append(paper)

        qids = [q['question_id'] for q in paper.questions]
        answers_list = []
        for i in range(4):
            answers = {}
            for qid in qids:
                correct = paper.answer_key[qid]
                prob = 0.4 + i * 0.15
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

    merge_result = system.merge_exam_results([p.paper_id for p in all_papers])

    student_trend = merge_result.get_knowledge_trend('S004')
    assert student_trend is not None, "应该能获取学生知识点趋势"
    assert 'knowledge_points' in student_trend
    assert 'weak_points' in student_trend
    assert 'consecutive_weak_points' in student_trend

    assert student_trend['total_exams'] == 3, "应该有3场考试"
    assert student_trend['taken_exams'] == 3, "学生应该参加了3场"

    for kp, info in student_trend['knowledge_points'].items():
        assert 'avg_mastery' in info
        assert 'trend' in info
        assert 'consecutive_weak_count' in info
        assert 'last_change' in info
        assert 'mastery_history' in info
        assert len(info['mastery_history']) == 3, "应该有3场的记录"
        assert info['exam_count'] >= 1

    report = merge_result.generate_knowledge_trend_report('S004')
    assert isinstance(report, str) and len(report) > 0
    assert '知识点掌握变化报告' in report
    assert '连续薄弱' in report or '持续优秀' in report or '上升' in report or '下降' in report

    json_str = merge_result.export_to_json()
    json_data = json.loads(json_str)
    assert 'student_growth_profile' in json_data, "JSON导出应该包含学生成长档案"
    assert 'S001' in json_data['student_growth_profile'], "应该包含学生数据"

    csv_str = merge_result.export_to_csv()
    lines = csv_str.strip().split('\n')
    assert len(lines) >= 2, "CSV应该至少有表头和一行数据"
    header = lines[0].split(',')
    assert any('趋势' in h for h in header), "CSV表头应该包含趋势列"

    os.makedirs('output', exist_ok=True)
    json_file = merge_result.export_to_json('output/growth_test.json')
    csv_file = merge_result.export_to_csv('output/growth_test.csv')
    assert os.path.exists(json_file)
    assert os.path.exists(csv_file)

def test_duplicate_resolution():
    """测试3: 重复提交处理策略"""
    system = ExamSystem()

    with open('sample_questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    system.import_questions(data['questions'])

    rule1 = ExamRule(
        total_questions=5, num_versions=1,
        exam_title='测试场',
        difficulty_ratio={'easy': 0.6, 'medium': 0.4, 'hard': 0},
    )
    paper1 = system.generate_exam(rule1, seed=1)[0]

    rule2 = ExamRule(
        total_questions=5, num_versions=1,
        exam_title='测试场B',
        difficulty_ratio={'easy': 0.4, 'medium': 0.4, 'hard': 0.2},
    )
    paper2 = system.generate_exam(rule2, seed=2)[0]

    import random
    random.seed(123)

    all_results = []
    for paper_idx, paper in enumerate([paper1, paper2], 1):
        qids = [q['question_id'] for q in paper.questions]
        answers_list = []
        for i in range(3):
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
                'student_name': '学生1高分版',
                'paper_id': paper2.paper_id,
                'answers': {qid: paper2.answer_key[qid] for qid in qids},
            })
            answers_list.append({
                'student_id': 'S002',
                'student_name': '学生2低分版',
                'paper_id': paper2.paper_id,
                'answers': {qid: ['X'] for qid in qids},
            })
        results = system.grade_exam(paper.paper_id, answers_list)
        all_results.append(results)

    merge_raw = ExamGrader.merge_exam_results(all_results)
    assert len(merge_raw.duplicates) > 0, "应该有重复记录"

    merge_highest = merge_raw.resolve_duplicates('highest_score')
    assert merge_highest is not None
    s001_highest = merge_highest.get_student_summary('S001')
    assert s001_highest is not None

    merge_earliest = merge_raw.resolve_duplicates('earliest')
    s001_earliest = merge_earliest.get_student_summary('S001')
    assert s001_earliest is not None

    s002_highest = merge_highest.get_student_summary('S002')
    s002_earliest = merge_earliest.get_student_summary('S002')

    assert s002_highest['total_score'] >= s002_earliest['total_score'], \
        "最高分策略的总分应该 >= 最早策略"

    merge_manual = merge_raw.resolve_duplicates('manual')
    assert any('人工处理' in e for e in merge_manual.errors), "人工模式应该有错误提示"

    json_highest = json.loads(merge_highest.export_to_json())
    assert json_highest['summary']['duplicate_strategy'] != '未处理', "处理后应该标记为已处理"

    try:
        merge_raw.resolve_duplicates('invalid_strategy')
        assert False, "无效策略应该抛出异常"
    except ValueError as e:
        assert '策略' in str(e) or 'strategy' in str(e).lower()

def test_knowledge_trend_accuracy():
    """测试4: 知识点趋势准确性验证"""
    system = ExamSystem()

    bank = QuestionBank()

    kp_name = '测试知识点A'
    questions_easy = []
    for i in range(3):
        q = Question(
            question_id=f'QA{i+1}',
            content=f'A类题{i+1}',
            options=['正确', '错误1', '错误2', '错误3'],
            correct_answer=['A'],
            knowledge_points=[kp_name],
            difficulty='easy',
            score=10,
        )
        bank.add_question(q)
        questions_easy.append(q)

    kp_name2 = '测试知识点B'
    questions_b = []
    for i in range(3):
        q = Question(
            question_id=f'QB{i+1}',
            content=f'B类题{i+1}',
            options=['正确', '错误1', '错误2', '错误3'],
            correct_answer=['A'],
            knowledge_points=[kp_name2],
            difficulty='easy',
            score=10,
        )
        bank.add_question(q)
        questions_b.append(q)

    generator = ExamGenerator(bank)
    rule = ExamRule(
        total_questions=6,
        num_versions=1,
        shuffle_options=False,
        shuffle_questions=False,
        same_questions=True,
        exam_title='知识点趋势测试',
        difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
    )
    paper = generator.generate_exam(rule, seed=1)[0]

    all_results = []

    student_profiles = [
        {
            'id': 'S_FULL', 'name': '全对学生',
            'exam_scores': [1.0, 1.0, 1.0],
            'kpA_scores': [1.0, 1.0, 1.0],
            'kpB_scores': [1.0, 1.0, 1.0],
        },
        {
            'id': 'S_ZERO', 'name': '全错学生',
            'exam_scores': [0.0, 0.0, 0.0],
            'kpA_scores': [0.0, 0.0, 0.0],
            'kpB_scores': [0.0, 0.0, 0.0],
        },
        {
            'id': 'S_HALF', 'name': '半对半错学生',
            'exam_scores': [0.5, 0.5, 0.5],
            'kpA_scores': [1.0, 1.0, 1.0],
            'kpB_scores': [0.0, 0.0, 0.0],
        },
        {
            'id': 'S_IMPROVE', 'name': '进步学生',
            'exam_scores': [0.3, 0.6, 0.9],
            'kpA_scores': [0.3, 0.6, 0.9],
            'kpB_scores': [0.3, 0.6, 0.9],
        },
        {
            'id': 'S_DECLINE', 'name': '退步学生',
            'exam_scores': [0.9, 0.6, 0.3],
            'kpA_scores': [0.9, 0.6, 0.3],
            'kpB_scores': [0.9, 0.6, 0.3],
        },
    ]

    for exam_idx in range(3):
        paper_seed = 100 + exam_idx
        paper = generator.generate_exam(ExamRule(
            total_questions=6, num_versions=1,
            shuffle_options=False, shuffle_questions=False,
            exam_title=f'考试{exam_idx+1}',
            difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
        ), seed=paper_seed)[0]

        answers_list = []
        qids = [q['question_id'] for q in paper.questions]

        for profile in student_profiles:
            answers = {}
            for qid in qids:
                correct = paper.answer_key[qid]
                q = next(q for q in paper.questions if q['question_id'] == qid)
                kp = q['knowledge_points'][0]

                if kp == kp_name:
                    prob = profile['kpA_scores'][exam_idx]
                else:
                    prob = profile['kpB_scores'][exam_idx]

                import random
                if random.random() < prob:
                    answers[qid] = correct
                else:
                    answers[qid] = ['B'] if 'B' not in correct else ['C']

            answers_list.append({
                'student_id': profile['id'],
                'student_name': profile['name'],
                'paper_id': paper.paper_id,
                'answers': answers,
            })

        grader = ExamGrader(paper)
        results = []
        for sa_dict in answers_list:
            sa = StudentAnswer(
                sa_dict['student_id'], sa_dict['student_name'],
                sa_dict['paper_id'], sa_dict['answers']
            )
            result = grader.grade(sa)
            results.append(result)

        all_results.append(results)

    merge_result = ExamGrader.merge_exam_results(all_results)

    full_trend = merge_result.get_knowledge_trend('S_FULL')
    assert full_trend is not None
    assert full_trend['knowledge_points'][kp_name]['avg_mastery'] >= 0.8, \
        f"全对学生的知识点A掌握度应该>=0.8，实际是{full_trend['knowledge_points'][kp_name]['avg_mastery']}"
    assert full_trend['knowledge_points'][kp_name]['is_consistently_strong'], \
        "全对学生应该被标记为持续优秀"

    zero_trend = merge_result.get_knowledge_trend('S_ZERO')
    assert zero_trend['knowledge_points'][kp_name]['is_weak'], \
        "全错学生应该被标记为连续薄弱"
    assert zero_trend['knowledge_points'][kp_name]['consecutive_weak_count'] >= 2, \
        f"全错学生连续薄弱次数应该>=2，实际是{zero_trend['knowledge_points'][kp_name]['consecutive_weak_count']}"

    half_trend = merge_result.get_knowledge_trend('S_HALF')
    assert half_trend['knowledge_points'][kp_name]['avg_mastery'] > 0.7, \
        f"半对学生的知识点A掌握度应该>0.7，实际是{half_trend['knowledge_points'][kp_name]['avg_mastery']}"
    assert half_trend['knowledge_points'][kp_name2]['avg_mastery'] < 0.3, \
        f"半对学生的知识点B掌握度应该<0.3，实际是{half_trend['knowledge_points'][kp_name2]['avg_mastery']}"

    improve_trend = merge_result.get_knowledge_trend('S_IMPROVE')
    kpA_info = improve_trend['knowledge_points'][kp_name]
    assert kpA_info['last_mastery'] > kpA_info['first_mastery'], \
        f"进步学生的掌握度应该上升，首{kpA_info['first_mastery']} 末{kpA_info['last_mastery']}"

    report = merge_result.generate_knowledge_trend_report('S_FULL')
    assert '持续优秀' in report, "全对学生报告应该包含持续优秀"

    zero_report = merge_result.generate_knowledge_trend_report('S_ZERO')
    assert '连续薄弱' in zero_report, "全错学生报告应该包含连续薄弱"

    class_trend = merge_result.get_class_knowledge_trend()
    assert len(class_trend['knowledge_points']) >= 2, "应该至少有2个知识点的班级统计"

if __name__ == '__main__':
    print("=" * 70)
    print("综合测试 - 验证4项新功能")
    print("=" * 70)
    print()

    run_test("测试1: 同题多卷模式", test_same_questions_mode)
    run_test("测试2: 学生成长档案", test_student_growth_profile)
    run_test("测试3: 重复提交处理策略", test_duplicate_resolution)
    run_test("测试4: 知识点趋势准确性", test_knowledge_trend_accuracy)

    print()
    print("=" * 70)
    print(f"测试结果: 通过 {pass_count}, 失败 {fail_count}")
    print("=" * 70)

    if fail_count > 0:
        sys.exit(1)
    else:
        print("\n所有测试通过!")
        sys.exit(0)
