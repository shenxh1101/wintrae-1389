"""
测试代码：教育测评系统类库
"""

import json
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from edu_exam_lib import (
    Question,
    ExamRule,
    ExamPaper,
    StudentAnswer,
    ExamResult,
    QuestionBank,
    ExamGenerator,
    ExamGrader,
    ExamStatistics,
    ExamSystem,
    generate_exam,
    grade_exam,
    analyze_results,
    DifficultyLevel,
    QuestionType,
)


def test_question():
    """测试Question类"""
    print("测试 Question 类...", end=" ")

    q = Question(
        question_id="T001",
        content="测试题目",
        options=["A选项", "B选项", "C选项", "D选项"],
        correct_answer=["A"],
        knowledge_points=["测试知识点"],
        difficulty="easy",
        question_type="single_choice",
        score=2,
    )

    assert q.question_id == "T001"
    assert q.difficulty == DifficultyLevel.EASY
    assert q.question_type == QuestionType.SINGLE_CHOICE
    assert q.is_correct(["A"]) == True
    assert q.is_correct(["B"]) == False
    assert q.is_correct(["a"]) == True

    q2 = Question(
        question_id="T002",
        content="多选题目",
        options=["A", "B", "C", "D"],
        correct_answer=["A", "B"],
        knowledge_points=["测试"],
        difficulty="medium",
        question_type="multiple_choice",
    )
    assert q2.is_correct(["A", "B"]) == True
    assert q2.is_correct(["B", "A"]) == True
    assert q2.is_correct(["A"]) == False

    print("OK")


def test_question_bank():
    """测试QuestionBank类"""
    print("测试 QuestionBank 类...", end=" ")

    bank = QuestionBank()

    questions = [
        Question(
            question_id=f"Q{i:03d}",
            content=f"题目{i}",
            options=["A", "B", "C", "D"],
            correct_answer=["A"],
            knowledge_points=["知识点1", "知识点2"] if i % 2 == 0 else ["知识点1"],
            difficulty="easy" if i < 3 else "medium",
            question_type="single_choice" if i < 5 else "multiple_choice",
            score=2,
        )
        for i in range(10)
    ]

    errors = bank.add_questions(questions)
    assert len(errors) == 0
    assert len(bank) == 10

    kp1 = bank.filter_by_knowledge(["知识点1"])
    assert len(kp1) == 10

    kp2 = bank.filter_by_knowledge(["知识点2"])
    assert len(kp2) == 5

    easy = bank.filter_by_difficulty(DifficultyLevel.EASY)
    assert len(easy) == 3

    single = bank.filter_by_type(QuestionType.SINGLE_CHOICE)
    assert len(single) == 5

    filtered = bank.filter_complex(
        knowledge_points=["知识点1"],
        difficulty=DifficultyLevel.MEDIUM,
    )
    assert len(filtered) == 7

    selected = bank.select_by_difficulty_ratio(
        bank.get_all_questions(),
        5,
        {DifficultyLevel.EASY: 0.4, DifficultyLevel.MEDIUM: 0.6, DifficultyLevel.HARD: 0}
    )
    assert len(selected) == 5

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({'questions': [q.to_dict() for q in questions[:5]]}, f, ensure_ascii=False)
        temp_file = f.name

    try:
        bank2 = QuestionBank()
        count, errors = bank2.import_from_json(temp_file)
        assert count == 5
        assert len(errors) == 0
    finally:
        os.unlink(temp_file)

    print("OK")


def test_exam_generator():
    """测试ExamGenerator类"""
    print("测试 ExamGenerator 类...", end=" ")

    bank = QuestionBank()
    questions = [
        Question(
            question_id=f"Q{i:03d}",
            content=f"题目{i}",
            options=["A选项", "B选项", "C选项", "D选项"],
            correct_answer=["A"],
            knowledge_points=["Python基础"],
            difficulty="easy" if i < 3 else "medium",
            question_type="single_choice",
            score=2,
        )
        for i in range(10)
    ]
    bank.add_questions(questions)

    generator = ExamGenerator(bank)

    rule = ExamRule(
        total_questions=5,
        difficulty_ratio={'easy': 0.4, 'medium': 0.6, 'hard': 0},
        num_versions=2,
        exam_title="测试试卷",
        exam_duration=30,
    )

    papers = generator.generate_exam(rule, seed=42)
    assert len(papers) == 2

    paper = papers[0]
    assert len(paper.questions) == 5
    assert paper.version == 'A'
    assert paper.title == "测试试卷"
    assert paper.total_score == 10

    for q in paper.questions:
        assert 'display_num' in q
        assert 'options' in q
        assert isinstance(q['options'], dict)

    assert len(paper.answer_key) == 5
    assert len(paper.option_mapping) == 5

    answer_sheet = generator.generate_answer_sheet(paper)
    assert "答题卡" in answer_sheet
    assert "姓名" in answer_sheet

    answer_key = generator.generate_answer_key(paper)
    assert "标准答案" in answer_key

    printable = generator.generate_printable_exam(paper)
    assert "测试试卷" in printable
    assert "选择题" in printable

    printable_sheet = generator.generate_printable_answer_sheet(paper)
    assert "答 题 卡" in printable_sheet

    with tempfile.TemporaryDirectory() as tmpdir:
        files = generator.export_paper_to_files(paper, tmpdir, "test")
        assert os.path.exists(files['paper'])
        assert os.path.exists(files['answer_sheet'])
        assert os.path.exists(files['answer_key'])

    print("OK")


def test_exam_grader():
    """测试ExamGrader类"""
    print("测试 ExamGrader 类...", end=" ")

    bank = QuestionBank()
    questions = [
        Question(
            question_id=f"Q{i:03d}",
            content=f"题目{i}",
            options=["A", "B", "C", "D"],
            correct_answer=["A"],
            knowledge_points=["知识点1"],
            difficulty="easy",
            question_type="single_choice",
            score=2,
        )
        for i in range(5)
    ]
    bank.add_questions(questions)

    generator = ExamGenerator(bank)
    rule = ExamRule(total_questions=5, num_versions=1)
    paper = generator.generate_exam(rule, seed=42)[0]

    grader = ExamGrader(paper)

    qids = [q['question_id'] for q in paper.questions]

    correct_answers = {qid: paper.answer_key[qid] for qid in qids}
    sa_correct = StudentAnswer(
        student_id="S001",
        student_name="全对学生",
        paper_id=paper.paper_id,
        answers=correct_answers,
    )
    result = grader.grade(sa_correct)
    assert result.total_score == 10
    assert result.percentage == 100
    assert len(result.question_results) == 5
    assert all(qr.is_correct for qr in result.question_results)
    assert len(result.error_reasons) == 0

    wrong_answers = {}
    for qid in qids:
        correct = paper.answer_key[qid]
        options = ['A', 'B', 'C', 'D']
        wrong = [o for o in options if o not in correct]
        wrong_answers[qid] = [wrong[0]] if wrong else []

    sa_wrong = StudentAnswer(
        student_id="S002",
        student_name="全错学生",
        paper_id=paper.paper_id,
        answers=wrong_answers,
    )
    result2 = grader.grade(sa_wrong)
    assert result2.total_score == 0
    assert result2.percentage == 0
    assert len(result2.error_reasons) == 5

    partial_answers = {}
    for i, qid in enumerate(qids):
        correct = paper.answer_key[qid]
        if i < 3:
            partial_answers[qid] = correct
        else:
            options = ['A', 'B', 'C', 'D']
            wrong = [o for o in options if o not in correct]
            partial_answers[qid] = [wrong[0]] if wrong else []

    sa_partial = StudentAnswer(
        student_id="S003",
        student_name="部分对学生",
        paper_id=paper.paper_id,
        answers=partial_answers,
    )
    result3 = grader.grade(sa_partial)
    assert result3.total_score == 6
    assert result3.percentage == 60

    bad_sa = StudentAnswer(
        student_id="S999",
        student_name="错误答案",
        paper_id=paper.paper_id,
        answers={qids[0]: ['A'], 'INVALID': ['B']},
    )
    is_valid, errors, missing = grader.validate_answers(bad_sa)
    assert not is_valid
    assert len(errors) > 0

    missing_sa = StudentAnswer(
        student_id="S888",
        student_name="缺题学生",
        paper_id=paper.paper_id,
        answers={qids[0]: ['A']},
    )
    is_valid, errors, missing = grader.validate_answers(missing_sa)
    assert is_valid
    assert len(missing) == 4

    report = grader.generate_grade_report(result)
    assert "成绩报告单" in report
    assert "全对学生" in report

    print("OK")


def test_exam_statistics():
    """测试ExamStatistics类"""
    print("测试 ExamStatistics 类...", end=" ")

    bank = QuestionBank()
    questions = [
        Question(
            question_id=f"Q{i:03d}",
            content=f"题目{i}",
            options=["A", "B", "C", "D"],
            correct_answer=["A"],
            knowledge_points=["知识点1"] if i < 3 else ["知识点2"],
            difficulty="easy" if i < 2 else "medium",
            question_type="single_choice",
            score=2,
        )
        for i in range(5)
    ]
    bank.add_questions(questions)

    generator = ExamGenerator(bank)
    rule = ExamRule(total_questions=5, num_versions=1)
    paper = generator.generate_exam(rule, seed=42)[0]
    grader = ExamGrader(paper)

    qids = [q['question_id'] for q in paper.questions]
    results = []

    for i in range(10):
        answers = {}
        for j, qid in enumerate(qids):
            correct = paper.answer_key[qid]
            if j < i % 5 + 1:
                answers[qid] = correct
            else:
                options = ['A', 'B', 'C', 'D']
                wrong = [o for o in options if o not in correct]
                answers[qid] = [wrong[0]] if wrong else []

        sa = StudentAnswer(
            student_id=f"S{i:03d}",
            student_name=f"学生{i}",
            paper_id=paper.paper_id,
            answers=answers,
        )
        results.append(grader.grade(sa))

    stats = ExamStatistics(results)

    desc = stats.get_descriptive_stats()
    assert desc['count'] == 10
    assert 'mean' in desc
    assert 'median' in desc
    assert 'std_dev' in desc

    dist = stats.get_score_distribution()
    assert len(dist) == 5

    kp_stats = stats.get_knowledge_point_stats()
    assert '知识点1' in kp_stats
    assert '知识点2' in kp_stats

    q_stats = stats.get_question_stats()
    assert len(q_stats) == 5

    err_stats = stats.get_error_reason_stats()
    assert len(err_stats) > 0

    diff_stats = stats.get_difficulty_stats()
    assert 'easy' in diff_stats
    assert 'medium' in diff_stats

    ranks = stats.rank_students()
    assert len(ranks) == 10
    assert ranks[0]['percentage'] >= ranks[-1]['percentage']

    report = stats.generate_statistics_report()
    assert "统计分析报告" in report
    assert "成绩分段统计" in report

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        temp_file = f.name

    try:
        stats.export_statistics(temp_file, format='json')
        assert os.path.exists(temp_file)
    finally:
        os.unlink(temp_file)

    print("OK")


def test_exam_system():
    """测试ExamSystem类"""
    print("测试 ExamSystem 类...", end=" ")

    system = ExamSystem()

    questions_data = [
        {
            "question_id": f"Q{i:03d}",
            "content": f"题目{i}",
            "options": ["A", "B", "C", "D"],
            "correct_answer": ["A"],
            "knowledge_points": ["测试知识点"],
            "difficulty": "easy",
            "question_type": "single_choice",
            "score": 2,
        }
        for i in range(10)
    ]

    count, errors = system.import_questions(questions_data)
    assert count == 10
    assert len(errors) == 0

    bank_stats = system.get_bank_stats()
    assert bank_stats['total_questions'] == 10

    rule = ExamRule(total_questions=5, num_versions=1, exam_title="系统测试")
    papers = system.generate_exam(rule, seed=42)
    assert len(papers) == 1

    paper_id = papers[0].paper_id
    paper = system.get_exam_paper(paper_id)
    assert paper is not None

    qids = [q['question_id'] for q in paper.questions]
    student_answers = []
    for i in range(5):
        answers = {}
        for qid in qids:
            correct = paper.answer_key[qid]
            if i < 3:
                answers[qid] = correct
            else:
                options = ['A', 'B', 'C', 'D']
                wrong = [o for o in options if o not in correct]
                answers[qid] = [wrong[0]] if wrong else []
        student_answers.append({
            "student_id": f"S{i:03d}",
            "student_name": f"学生{i}",
            "paper_id": paper_id,
            "answers": answers,
        })

    results = system.grade_exam(paper_id, student_answers)
    assert len(results) == 5

    saved_results = system.get_results(paper_id)
    assert len(saved_results) == 5

    analysis = system.analyze_results(paper_id)
    assert analysis is not None

    papers_list = system.list_exam_papers()
    assert len(papers_list) == 1

    content = system.generate_printable_content(paper_id, 'paper')
    assert "系统测试" in content

    report = system.generate_grade_report(results[0])
    assert "成绩报告单" in report

    print("OK")


def test_simple_api():
    """测试简单API函数"""
    print("测试 简单API 函数...", end=" ")

    questions = [
        {
            "question_id": f"Q{i:03d}",
            "content": f"题目{i}",
            "options": ["A", "B", "C", "D"],
            "correct_answer": ["A"],
            "knowledge_points": ["API测试"],
            "difficulty": "easy",
            "question_type": "single_choice",
            "score": 2,
        }
        for i in range(10)
    ]

    rule = {
        'total_questions': 5,
        'num_versions': 1,
        'exam_title': 'API测试',
    }

    papers, bank_stats = generate_exam(questions, rule, seed=42)
    assert len(papers) == 1
    assert bank_stats['total_questions'] == 10

    paper = papers[0]
    qids = [q['question_id'] for q in paper.questions]

    answers1 = {qid: paper.answer_key[qid] for qid in qids}
    answers2 = {}
    for qid in qids:
        correct = paper.answer_key[qid]
        options = ['A', 'B', 'C', 'D']
        wrong = [o for o in options if o not in correct]
        answers2[qid] = [wrong[0]] if wrong else []

    student_answers = [
        {
            "student_id": "S001",
            "student_name": "API学生1",
            "paper_id": paper.paper_id,
            "answers": answers1,
        },
        {
            "student_id": "S002",
            "student_name": "API学生2",
            "paper_id": paper.paper_id,
            "answers": answers2,
        },
    ]

    results, validation = grade_exam(paper, student_answers, questions=questions)
    assert len(results) == 2
    assert validation['valid_answers'] == 2

    analysis = analyze_results(results)
    assert 'report' in analysis
    assert 'descriptive' in analysis

    print("OK")


def test_merge_results():
    """测试合并结果"""
    print("测试 结果合并 功能...", end=" ")

    bank = QuestionBank()
    questions = [
        Question(
            question_id=f"Q{i:03d}",
            content=f"题目{i}",
            options=["A", "B", "C", "D"],
            correct_answer=["A"],
            knowledge_points=["合并测试"],
            difficulty="easy",
            question_type="single_choice",
            score=2,
        )
        for i in range(5)
    ]
    bank.add_questions(questions)

    generator = ExamGenerator(bank)
    rule1 = ExamRule(total_questions=3, num_versions=1, exam_title="第一场")
    paper1 = generator.generate_exam(rule1, seed=1)[0]

    rule2 = ExamRule(total_questions=3, num_versions=1, exam_title="第二场")
    paper2 = generator.generate_exam(rule2, seed=2)[0]

    grader1 = ExamGrader(paper1)
    grader2 = ExamGrader(paper2)

    qids1 = [q['question_id'] for q in paper1.questions]
    qids2 = [q['question_id'] for q in paper2.questions]

    results1 = []
    for i in range(3):
        sa = StudentAnswer(
            student_id=f"S{i+1:03d}",
            student_name=f"学生{i+1}",
            paper_id=paper1.paper_id,
            answers={qid: paper1.answer_key[qid] for qid in qids1},
        )
        results1.append(grader1.grade(sa))

    results2 = []
    for i in range(3):
        sa = StudentAnswer(
            student_id=f"S{i+1:03d}",
            student_name=f"学生{i+1}",
            paper_id=paper2.paper_id,
            answers={qid: paper2.answer_key[qid] for qid in qids2},
        )
        results2.append(grader2.grade(sa))

    merge_result = ExamGrader.merge_exam_results([results1, results2])
    assert len(merge_result.merged_results) == 6

    print("OK")


def test_error_handling():
    """测试错误处理"""
    print("测试 错误处理 功能...", end=" ")

    bank = QuestionBank()
    q = Question(
        question_id="E001",
        content="测试",
        options=["A", "B"],
        correct_answer=["A"],
        knowledge_points=["测试"],
        difficulty="easy",
        question_type="single_choice",
    )
    bank.add_question(q)

    try:
        bank.add_question(q)
        assert False, "应该抛出重复ID错误"
    except ValueError as e:
        assert "已存在" in str(e)

    try:
        ExamRule(total_questions=0)
        assert False, "应该抛出规则验证错误"
    except ValueError:
        pass

    generator = ExamGenerator(bank)
    rule = ExamRule(total_questions=5, difficulty_ratio={'easy': 1})
    try:
        generator.generate_exam(rule)
        assert False, "应该抛出题目不足错误"
    except ValueError as e:
        assert "不足" in str(e)

    rule2 = ExamRule(
        total_questions=1,
        difficulty_ratio={'easy': 0.5, 'medium': 0.6},
    )
    try:
        generator.generate_exam(rule2)
        assert False, "应该抛出比例错误"
    except ValueError as e:
        assert "比例" in str(e)

    paper = generator.generate_exam(ExamRule(total_questions=1))[0]
    grader = ExamGrader(paper)

    sa_missing = StudentAnswer(
        student_id="E001",
        student_name="缺题",
        paper_id=paper.paper_id,
        answers={},
    )
    try:
        grader.grade(sa_missing)
        assert False, "应该抛出缺失答案错误"
    except ValueError as e:
        assert "缺失答案" in str(e)

    sa_bad_qid = StudentAnswer(
        student_id="E002",
        student_name="坏题号",
        paper_id=paper.paper_id,
        answers={'BAD_ID': ['A'], paper.questions[0]['question_id']: ['A']},
    )
    try:
        grader.grade(sa_bad_qid)
        assert False, "应该抛出题号不存在错误"
    except ValueError as e:
        assert "不在试卷中" in str(e)

    print("OK")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("运行教育测评系统类库测试")
    print("=" * 60)
    print()

    tests = [
        test_question,
        test_question_bank,
        test_exam_generator,
        test_exam_grader,
        test_exam_statistics,
        test_exam_system,
        test_simple_api,
        test_merge_results,
        test_error_handling,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAILED: {test.__name__}")
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"测试完成: {passed} 个通过, {failed} 个失败")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
