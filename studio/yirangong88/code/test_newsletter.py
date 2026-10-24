import copy
import json
import unittest
from newsletter import ROOT, previous_day, render


class NewsletterTests(unittest.TestCase):
    def test_eastern_date_boundary(self):
        self.assertEqual(previous_day('2026-09-17T01:00:00Z'), '2026-09-15')

    def test_dst_calendar_day(self):
        self.assertEqual(previous_day('2026-03-09T04:30:00Z'), '2026-03-08')

    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            previous_day('2026-09-17T12:00:00')

    def test_selection_and_missing_input(self):
        data = json.loads((ROOT / 'outputs/evidence-run-03.json').read_text())
        result, decisions = render(data)
        self.assertEqual(sum(d['decision'] == 'include' for d in decisions), 3)
        self.assertNotIn('Introducing Astra for Law', result)
        broken = copy.deepcopy(data)
        del broken['candidates'][0]['fact']
        with self.assertRaises(ValueError):
            render(broken)


if __name__ == '__main__':
    unittest.main()
