"""
综合测试 - 验证第4轮4项新功能
1. 班级-知识点维度对比报告（薄弱人数变化、连续退步知识点）
2. 学生成长档案可打印文本汇总 + JSON/CSV/文本字段对齐
3. 重复提交最早提交策略按提交时间判断
4. 版本对照表长选项不截断 + CSV重复提交标记与JSON对齐
"""

import json
import csv
import sys
import os
sys.path.insert(0, os.getcwd())

from edu_exam_lib import (
    QuestionBank, ExamGenerator, ExamRule, Question,
    StudentAnswer, ExamGrader, ExamStatistics,
    ExamSystem, MergeResult, ExamResult
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
        print(f"[FAILED] {name}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        fail_count += 1


def _build_multi_exam_merge():
    """辅助函数: 构建多场考试合并结果"""
    system = ExamSystem()
    with open('sample_questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    system.import_questions(data['questions'])

    import random
    random.seed(888)

    all_results = []
    for exam_idx in range(3):
        rule = ExamRule(
            total_questions=8,
            num_versions=1,
            exam_title=f'第{exam_idx+1}场',
            difficulty_ratio={'easy': 0.5, 'medium': 0.3, 'hard': 0.2},
        )
        paper = system.generate_exam(rule, seed=200+exam_idx)[0]
        qids = [q['question_id'] for q in paper.questions]
        answers_list = []
        for i in range(5):
            answers = {}
            for qid in qids:
                correct = paper.answer_key[qid]
                prob = 0.3 + i * 0.15
                if random.random() < prob:
                    answers[qid] = correct
                else:
                    answers[qid] = ['A'] if 'A' not in correct else ['B']
            sa = StudentAnswer(
                f'S{i+1:03d}', f'学生{i+1}',
                paper.paper_id, answers,
                submitted_at=f'2026-06-2{exam_idx}T10:{i:02d}:00',
            )
            grader = ExamGrader(paper)
            result = grader.grade(sa)
            answers_list.append(result)
        all_results.append(answers_list)

    return ExamGrader.merge_exam_results(all_results)


def test_class_kp_comparison():
    """测试1: 班级-知识点维度对比报告"""
    merge_result = _build_multi_exam_merge()
    class_trend = merge_result.get_class_knowledge_trend()

    assert 'exam_weak_count' in str(class_trend), "应该有薄弱人数变化数据"
    assert 'continuously_declining_points' in class_trend, "应该有连续退步知识点"

    for kp, info in class_trend['knowledge_points'].items():
        assert 'exam_weak_count' in info, f"{kp} 应该有exam_weak_count"
        assert 'consecutive_decline_count' in info, f"{kp} 应该有consecutive_decline_count"
        assert 'is_continuously_declining' in info, f"{kp} 应该有is_continuously_declining"
        for exam_idx, wc in info['exam_weak_count'].items():
            assert 'weak_count' in wc
            assert 'total_count' in wc
            assert 'weak_rate' in wc

    report = merge_result.generate_knowledge_trend_report()
    assert '薄弱' in report, "报告应该包含薄弱信息"
    assert '场次' in report, "报告应该包含场次详情"

    json_str = merge_result.export_to_json()
    json_data = json.loads(json_str)
    assert 'class_knowledge_trend' in json_data, "JSON应该包含班级知识点趋势"
    ck = json_data['class_knowledge_trend']
    assert 'continuously_declining_points' in ck, "应该有连续退步知识点"
    for kp, info in ck['knowledge_points'].items():
        assert 'exam_weak_count' in info, f"JSON里{kp}应该有exam_weak_count"
        assert 'consecutive_decline_count' in info


def test_student_growth_summary():
    """测试2: 学生成长档案可打印文本汇总 + 字段对齐"""
    merge_result = _build_multi_exam_merge()

    trend = merge_result.get_knowledge_trend('S001')
    assert trend is not None
    for kp, info in trend['knowledge_points'].items():
        assert 'review_priority' in info, f"{kp}应该有review_priority"
        assert 'review_priority_rank' in info, f"{kp}应该有review_priority_rank"
        assert 'last_3_changes' in info, f"{kp}应该有last_3_changes"

    summary = merge_result.generate_student_growth_summary('S001')
    assert isinstance(summary, str) and len(summary) > 50
    assert '复习优先级' in summary, "应该有复习优先级"
    assert '学生:' in summary or '学生' in summary

    all_summary = merge_result.generate_student_growth_summary()
    assert 'S001' in all_summary or '学生1' in all_summary
    assert 'S005' in all_summary or '学生5' in all_summary

    os.makedirs('output', exist_ok=True)
    f = merge_result.export_student_growth_summary('output/growth_summary.txt')
    assert os.path.exists(f)

    json_str = merge_result.export_to_json()
    json_data = json.loads(json_str)
    assert 'student_growth_profile' in json_data
    profile = json_data['student_growth_profile']
    for sid, pdata in profile.items():
        for kp, kp_data in pdata['knowledge_points'].items():
            assert 'review_priority' in kp_data, f"JSON {sid}/{kp} 缺少review_priority"
            assert 'review_priority_rank' in kp_data, f"JSON {sid}/{kp} 缺少review_priority_rank"
            assert 'last_3_changes' in kp_data, f"JSON {sid}/{kp} 缺少last_3_changes"

    csv_str = merge_result.export_to_csv()
    lines = csv_str.strip().split('\n')
    header = lines[0].split(',')
    assert any('复习优先级排名' in h for h in header), "CSV应该有复习优先级排名列"
    assert any('最近掌握度' in h for h in header), "CSV应该有最近掌握度列"
    assert any('最近变化' in h for h in header), "CSV应该有最近变化列"


def test_earliest_by_submitted_at():
    """测试3: 最早提交策略按提交时间判断"""
    bank = QuestionBank()
    for i in range(3):
        bank.add_question(Question(
            question_id=f'Q{i+1}', content=f'题{i+1}',
            options=['A1', 'B1', 'C1', 'D1'],
            correct_answer=['A'],
            knowledge_points=[f'kp{i+1}'],
            difficulty='easy', score=10,
        ))

    generator = ExamGenerator(bank)
    rule = ExamRule(
        total_questions=3, num_versions=1,
        exam_title='提交时间测试',
        difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
    )
    paper = generator.generate_exam(rule, seed=1)[0]
    qids = [q['question_id'] for q in paper.questions]

    all_answers = []
    sa1 = StudentAnswer('S001', '学生1-早', paper.paper_id,
                        {qid: paper.answer_key[qid] for qid in qids},
                        submitted_at='2026-06-20T08:00:00')
    sa2 = StudentAnswer('S001', '学生1-晚', paper.paper_id,
                        {qid: ['B'] for qid in qids},
                        submitted_at='2026-06-20T09:00:00')
    sa3 = StudentAnswer('S002', '学生2', paper.paper_id,
                        {qid: paper.answer_key[qid] for qid in qids})

    grader = ExamGrader(paper)
    r1 = grader.grade(sa1)
    r2 = grader.grade(sa2)
    r3 = grader.grade(sa3)

    merge = ExamGrader.merge_exam_results([[r1, r2, r3]])
    assert len(merge.duplicates) > 0, "应该有重复记录"

    merge_earliest = merge.resolve_duplicates('earliest')
    s001 = merge_earliest.get_student_summary('S001')
    assert s001 is not None
    assert s001['total_score'] > 0, "最早提交的应该是全对的"

    dup_s001 = [d for d in merge_earliest.duplicates if d['student_id'] == 'S001']
    kept = [d for d in dup_s001 if d.get('kept')]
    assert len(kept) == 1, "应该保留一条"
    assert kept[0]['reason'] == '最早提交', f"原因应该是'最早提交'，实际是'{kept[0]['reason']}'"
    not_kept = [d for d in dup_s001 if not d.get('kept')]
    assert '提交时间' in not_kept[0].get('reason', ''), \
        f"被覆盖的原因应该提到提交时间，实际是'{not_kept[0]['reason']}'"

    bank2 = QuestionBank()
    for i in range(3):
        bank2.add_question(Question(
            question_id=f'Q{i+1}', content=f'题{i+1}',
            options=['A1', 'B1', 'C1', 'D1'],
            correct_answer=['A'],
            knowledge_points=[f'kp{i+1}'],
            difficulty='easy', score=10,
        ))
    generator2 = ExamGenerator(bank2)
    paper2 = generator2.generate_exam(ExamRule(
        total_questions=3, num_versions=1,
        exam_title='无提交时间测试',
        difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
    ), seed=5)[0]
    qids2 = [q['question_id'] for q in paper2.questions]

    sa_no_time1 = StudentAnswer('S001', '学生1先', paper2.paper_id,
                                {qid: paper2.answer_key[qid] for qid in qids2})
    sa_no_time2 = StudentAnswer('S001', '学生1后', paper2.paper_id,
                                {qid: ['B'] for qid in qids2})
    grader2 = ExamGrader(paper2)
    r_no1 = grader2.grade(sa_no_time1)
    r_no2 = grader2.grade(sa_no_time2)

    merge_no_time = ExamGrader.merge_exam_results([[r_no1, r_no2]])
    merge_earliest_no_time = merge_no_time.resolve_duplicates('earliest')
    s001_no = merge_earliest_no_time.get_student_summary('S001')
    assert s001_no is not None
    assert s001_no['total_score'] > 0, "没有提交时间时应该保留输入顺序中最早的(全对)"


def test_version_comparison_no_truncation():
    """测试4: 版本对照表长选项不截断"""
    bank = QuestionBank()
    long_option = "这是一个非常长的选项内容用来测试截断问题不应该被截断应该完整显示"
    bank.add_question(Question(
        question_id='Q001', content='长选项题',
        options=[long_option, '短选项B', '短选项C', '短选项D'],
        correct_answer=['A'],
        knowledge_points=['kp1'],
        difficulty='easy', score=10,
    ))
    bank.add_question(Question(
        question_id='Q002', content='普通题',
        options=['A2', 'B2', 'C2', 'D2'],
        correct_answer=['B'],
        knowledge_points=['kp2'],
        difficulty='easy', score=10,
    ))

    generator = ExamGenerator(bank)
    rule = ExamRule(
        total_questions=2, num_versions=2,
        shuffle_options=True, shuffle_questions=True,
        same_questions=True,
        exam_title='长选项测试',
        difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
    )
    papers = generator.generate_exam(rule, seed=42)

    comparison = generator.generate_version_comparison(papers)
    assert long_option in comparison, f"长选项应该完整显示，没有找到: {long_option[:30]}..."

    os.makedirs('output', exist_ok=True)
    out = generator.export_version_comparison(papers, 'output', 'long_opt_test')
    assert os.path.exists(out), "TXT文件应该存在"

    csv_path = os.path.join('output', 'long_opt_test_version_comparison.csv')
    assert os.path.exists(csv_path), "CSV文件应该存在"

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = list(csv.reader(f))
    assert len(reader) > 1, "CSV应该有数据行"
    csv_content = '\n'.join([','.join(row) for row in reader])
    assert long_option in csv_content, "CSV中长选项应该完整显示"

    header = reader[0]
    assert '题目ID' in header
    assert '选项A内容' in header
    assert '正确答案' in header


def test_csv_dup_marks_match_json():
    """测试5: CSV重复提交标记与JSON对齐"""
    bank = QuestionBank()
    for i in range(3):
        bank.add_question(Question(
            question_id=f'Q{i+1}', content=f'题{i+1}',
            options=['A1', 'B1', 'C1', 'D1'],
            correct_answer=['A'],
            knowledge_points=[f'kp{i+1}'],
            difficulty='easy', score=10,
        ))

    generator = ExamGenerator(bank)
    rule = ExamRule(
        total_questions=3, num_versions=1,
        exam_title='CSV标记测试',
        difficulty_ratio={'easy': 1, 'medium': 0, 'hard': 0},
    )
    paper = generator.generate_exam(rule, seed=1)[0]
    qids = [q['question_id'] for q in paper.questions]

    grader = ExamGrader(paper)
    r1 = grader.grade(StudentAnswer('S001', '学生1高', paper.paper_id,
                                     {qid: paper.answer_key[qid] for qid in qids},
                                     submitted_at='2026-06-20T10:00:00'))
    r2 = grader.grade(StudentAnswer('S001', '学生1低', paper.paper_id,
                                     {qid: ['B'] for qid in qids},
                                     submitted_at='2026-06-20T11:00:00'))
    r3 = grader.grade(StudentAnswer('S002', '学生2', paper.paper_id,
                                     {qid: paper.answer_key[qid] for qid in qids}))

    merge = ExamGrader.merge_exam_results([[r1, r2, r3]])
    merge_highest = merge.resolve_duplicates('highest_score')

    json_str = merge_highest.export_to_json()
    json_data = json.loads(json_str)
    s001_rank = next(r for r in json_data['ranking'] if r['student_id'] == 'S001')
    assert s001_rank['has_duplicate'] == True, "JSON中S001应该标记有重复"
    assert s001_rank['duplicate_count'] > 0, "JSON中S001重复数应该>0"

    csv_str = merge_highest.export_to_csv()
    lines = csv_str.strip().split('\n')
    header = lines[0].split(',')
    dup_total_idx = header.index('重复总条数')
    kept_idx = header.index('被保留条数')

    s001_row = None
    for line in lines[1:]:
        fields = line.split(',')
        if 'S001' in fields:
            s001_row = fields
            break
    assert s001_row is not None, "CSV中应该有S001"
    assert s001_row[dup_total_idx] == '2', f"S001重复总条数应该是2，实际是{s001_row[dup_total_idx]}"
    assert s001_row[kept_idx] == '1', f"S001被保留条数应该是1，实际是{s001_row[kept_idx]}"

    merge_manual = merge.resolve_duplicates('manual')
    csv_manual = merge_manual.export_to_csv()
    lines_m = csv_manual.strip().split('\n')
    header_m = lines_m[0].split(',')
    manual_idx = header_m.index('需人工处理')

    s001_m = None
    for line in lines_m[1:]:
        fields = line.split(',')
        if 'S001' in fields:
            s001_m = fields
            break
    assert s001_m is not None
    assert s001_m[manual_idx] == '是', "手动模式下CSV应该标记需人工处理"


if __name__ == '__main__':
    print("=" * 70)
    print("综合测试 - 验证第4轮4项新功能")
    print("=" * 70)
    print()

    run_test("测试1: 班级-知识点维度对比报告", test_class_kp_comparison)
    run_test("测试2: 学生成长档案文本汇总+字段对齐", test_student_growth_summary)
    run_test("测试3: 最早提交按提交时间判断", test_earliest_by_submitted_at)
    run_test("测试4: 版本对照表长选项不截断", test_version_comparison_no_truncation)
    run_test("测试5: CSV重复提交标记与JSON对齐", test_csv_dup_marks_match_json)

    print()
    print("=" * 70)
    print(f"测试结果: 通过 {pass_count}, 失败 {fail_count}")
    print("=" * 70)

    if fail_count > 0:
        sys.exit(1)
    else:
        print("\n所有测试通过!")
        sys.exit(0)
