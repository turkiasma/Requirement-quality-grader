import unittest

from harness.schemas import CRITERIA, RequirementCritique
from harness.scorer import score_critique


def gold(*criteria):
    return {key: key in criteria for key in CRITERIA}


def review(*criteria):
    return {'issues': [{'criterion': key, 'explanation': 'Issue.'} for key in criteria],
            'improved_requirement': 'Improved requirement.'}


class ScorerTests(unittest.TestCase):
    def test_missed_correct_false_and_unflagged_criteria(self):
        result = score_critique(gold('testable', 'clarity'), review('clarity', 'complete'))
        self.assertEqual(result, {
            'correctly_identified': ['clarity'], 'missed': ['testable'],
            'incorrectly_predicted': ['complete'], 'correctly_unflagged': ['atomic', 'feasible'],
            'counts': {'tp': 1, 'fn': 1, 'fp': 1, 'tn': 2}, 'exact_match': False,
        })

    def test_perfect_predictions_deduplicate_and_use_canonical_order(self):
        result = score_critique(gold('atomic', 'clarity'),
                                RequirementCritique(**review('clarity', 'atomic', 'clarity')))
        self.assertEqual(result['correctly_identified'], ['atomic', 'clarity'])
        self.assertEqual(result['counts'], {'tp': 2, 'fn': 0, 'fp': 0, 'tn': 3})
        self.assertTrue(result['exact_match'])

    def test_good_requirement_with_no_predictions(self):
        result = score_critique(gold(), review())
        self.assertEqual(result['counts'], {'tp': 0, 'fn': 0, 'fp': 0, 'tn': 5})
        self.assertTrue(result['exact_match'])

    def test_good_requirement_with_false_prediction(self):
        self.assertEqual(score_critique(gold(), review('atomic'))['incorrectly_predicted'],
                         ['atomic'])

    def test_no_predictions_misses_all_actual_issues(self):
        self.assertEqual(score_critique(gold('testable', 'complete'), review())['missed'],
                         ['testable', 'complete'])

    def test_rejects_invalid_gold(self):
        cases = [None, [], {}, dict(gold(), unknown=False)]
        cases += [dict(gold(), atomic=value) for value in (1, 0, 'true', None)]
        missing = gold()
        del missing['atomic']
        cases.append(missing)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                score_critique(value, review())

    def test_rejects_unknown_prediction(self):
        with self.assertRaises(ValueError):
            score_critique(gold(), review('atomicity'))


if __name__ == '__main__':
    unittest.main()
