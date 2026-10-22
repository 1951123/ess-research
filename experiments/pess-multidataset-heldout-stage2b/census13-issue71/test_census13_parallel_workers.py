import threading
import unittest

from run_census13_smoke import _parallel_worker_calls


class ParallelWorkerTests(unittest.TestCase):
    def test_two_worker_functions_overlap(self):
        barrier = threading.Barrier(2)
        def worker(value):
            barrier.wait(timeout=2)
            return [value]
        self.assertEqual(_parallel_worker_calls(worker, ((1,), (2,))), [1, 2])

    def test_rejects_wrong_worker_count(self):
        with self.assertRaises(ValueError):
            _parallel_worker_calls(lambda value: value, ((1,),))


if __name__ == "__main__":
    unittest.main()
