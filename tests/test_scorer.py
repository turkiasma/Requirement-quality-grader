import unittest

from harness.schemas import CRITERIA
from harness.scorer import compare_to_human, correction_direction, overall_score


def grades(**overrides):
    base = {key: 5 for key in CRITERIA}
    base.update(overrides)
    return base


class OverallScoreTests(unittest.TestCase):
    def test_perfect_score(self):
        self.assertEqual(overall_score(grades()), 5.0)

    def test_unrounded_average(self):
        g = grades(atomicity=5, testability=0, feasibility=5, clarity=2, completeness=1)
        self.assertAlmostEqual(overall_score(g), 2.6)

    def test_accepts_plain_or_wrapped_dict(self):
        g = grades(clarity=3)
        wrapped = {'criteria': {key: {'grade': value} for key, value in g.items()}}
        self.assertEqual(overall_score(g), overall_score(wrapped))


class CompareToHumanTests(unittest.TestCase):
    def test_exact_match(self):
        human = grades()
        result = compare_to_human(grades(), human)
        self.assertEqual(result['exact_match_count'], 5)
        self.assertTrue(result['all_five_match'])
        self.assertEqual(result['mean_absolute_error'], 0)
        self.assertTrue(result['overall_exact_match'])

    def test_partial_mismatch_and_within_one(self):
        human = grades()
        candidate = grades(clarity=4, completeness=2)  # diffs: -1, -3
        result = compare_to_human(candidate, human)
        self.assertEqual(result['exact_match_count'], 3)
        self.assertEqual(result['within_one_count'], 4)
        self.assertFalse(result['all_five_match'])
        self.assertAlmostEqual(result['mean_absolute_error'], (1 + 3) / 5)

    def test_identical_overall_score_different_criteria_still_distinguished(self):
        human = grades()
        candidate_a = grades(atomicity=4, testability=4, feasibility=4, clarity=4, completeness=4)
        candidate_b = grades(atomicity=0, testability=5, feasibility=5, clarity=5, completeness=5)
        result_a = compare_to_human(candidate_a, human)
        result_b = compare_to_human(candidate_b, human)
        self.assertEqual(result_a['overall_score'], result_b['overall_score'])
        self.assertEqual(result_a['overall_absolute_error'], result_b['overall_absolute_error'])
        # Same overall score and overall error, but per-criterion comparison tells them apart.
        self.assertNotEqual(result_a['exact_match_count'], result_b['exact_match_count'])

    def test_rejects_invalid_gold(self):
        cases = [None, [], {}, dict(grades(), unknown=5)]
        cases += [dict(grades(), atomicity=value) for value in (6, -1, 'true', None, True)]
        missing = grades()
        del missing['atomicity']
        cases.append(missing)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                compare_to_human(grades(), value)

    def test_rejects_incomplete_candidate(self):
        human = grades()
        incomplete = grades()
        del incomplete['atomicity']
        with self.assertRaises(ValueError):
            compare_to_human(incomplete, human)


class CorrectionDirectionTests(unittest.TestCase):
    def test_closer_farther_equal_classification(self):
        human = grades()  # all 5
        llm1 = grades(atomicity=3, testability=3, clarity=3)  # distance 2 each
        second = grades(atomicity=5, testability=1, clarity=3)  # closer(0), farther(4), equal(2)
        result = correction_direction(llm1, second, human)
        self.assertEqual(result['per_criterion']['atomicity']['direction'], 'closer')
        self.assertEqual(result['per_criterion']['testability']['direction'], 'farther')
        self.assertEqual(result['per_criterion']['clarity']['direction'], 'equal')
        self.assertEqual(result['tally'], {'closer': 1, 'farther': 1, 'equal': 3})

    def test_rejects_incomplete_inputs(self):
        human = grades()
        incomplete = grades()
        del incomplete['atomicity']
        with self.assertRaises(ValueError):
            correction_direction(incomplete, grades(), human)
        with self.assertRaises(ValueError):
            correction_direction(grades(), incomplete, human)


if __name__ == '__main__':
    unittest.main()
