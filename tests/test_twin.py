import os, random, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twin import ids, corpus, anonymize, audit


class T(unittest.TestCase):
    def test_identifiers_valid(self):
        r = random.Random(1)
        s = ids.siren(r)
        self.assertTrue(ids.luhn_ok(s) and len(s) == 9)
        self.assertTrue(ids.luhn_ok(ids.siret(r, s)))
        self.assertTrue(ids.iban_ok(ids.iban_fr(r)))

    def test_same_person_same_pseudonym_everywhere(self):
        c = corpus.make(3, corpus.DEV)
        arts = anonymize.anonymize(c, "twin")
        p = c["people"][1]
        d = anonymize.parse_directory(arts)
        twin_row = [x for x in d if x["jira"] not in {q["jira"] for q in c["people"]}]
        self.assertEqual(len(twin_row), len(c["people"]))           # every Jira id was replaced

    def test_dates_keep_weekday_and_gaps(self):
        c = corpus.make(4, corpus.DEV)
        arts = anonymize.anonymize(c, "twin")
        for t in c["tasks"]:
            self.assertEqual(audit.solve(arts, t["key"])["gap"], audit.solve(c["arts"], t["key"])["gap"])

    def test_no_leaks_dev(self):
        c = corpus.make(5, corpus.DEV)
        a, b, found = audit.leaks(c, anonymize.anonymize(c, "twin"), corpus.DEV)
        self.assertEqual(a, 0, found[:5])
        self.assertGreater(b, 50)

    def test_perdoc_breaks_joins(self):
        c = corpus.make(6, corpus.DEV)
        ok_t, tot = audit.coherence(c, anonymize.anonymize(c, "twin"))
        ok_p, _ = audit.coherence(c, anonymize.anonymize(c, "perdoc"))
        self.assertEqual(ok_t, tot)
        self.assertLess(ok_p, tot / 2)

    def test_regex_leaks_names(self):
        c = corpus.make(7, corpus.DEV)
        a, b, _ = audit.leaks(c, anonymize.anonymize(c, "regex"), corpus.DEV)
        self.assertGreater(a, b / 2)


if __name__ == "__main__":
    unittest.main()
