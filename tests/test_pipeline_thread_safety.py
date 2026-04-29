import threading
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.config.singleton import SingletonMeta


class TestPipelineThreadSafety:
    def test_concurrent_access_from_multiple_threads(self, tmp_dir):
        db = tmp_dir / "test_thread.db"
        pm = PipelineManager(db)
        errors = []
        results = {}

        def worker(thread_id):
            try:
                with pm:
                    pm.upsert_job(f"job_t{thread_id}", job_name=f"Thread{thread_id}")
                    job = pm.get_job(f"job_t{thread_id}")
                    results[thread_id] = job is not None and job["job_name"] == f"Thread{thread_id}"
            except Exception as e:
                errors.append((thread_id, str(e)))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"线程安全错误: {errors}"
        assert all(results.values()), f"部分线程结果不正确: {results}"

    def test_concurrent_read_write(self, tmp_dir):
        db = tmp_dir / "test_rw.db"
        pm = PipelineManager(db)
        with pm:
            pm.upsert_job("shared_job", job_name="Shared")

        errors = []

        def reader():
            try:
                with pm:
                    job = pm.get_job("shared_job")
                    assert job is not None
            except Exception as e:
                errors.append(("reader", str(e)))

        def writer():
            try:
                with pm:
                    pm.update_score("shared_job", 4.0, "B")
            except Exception as e:
                errors.append(("writer", str(e)))

        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=reader))
            threads.append(threading.Thread(target=writer))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"并发读写错误: {errors}"

    def test_each_thread_gets_own_connection(self, tmp_dir):
        db = tmp_dir / "test_conn.db"
        pm = PipelineManager(db)
        with pm:
            pass
        conn_ids = {}
        barrier = threading.Barrier(2, timeout=5)

        def worker(thread_id):
            with pm:
                conn = pm._conn
                conn_ids[thread_id] = id(conn)
                barrier.wait(timeout=5)

        t1 = threading.Thread(target=worker, args=(1,))
        t2 = threading.Thread(target=worker, args=(2,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert conn_ids[1] != conn_ids[2], "不同线程应使用不同的连接"

    def test_ref_count_per_thread(self, tmp_dir):
        db = tmp_dir / "test_refcount.db"
        pm = PipelineManager(db)
        with pm:
            pass
        ref_counts = {}
        barrier = threading.Barrier(2, timeout=5)

        def worker(thread_id):
            with pm:
                ref_counts[thread_id] = pm._ref_count
                barrier.wait(timeout=5)

        t1 = threading.Thread(target=worker, args=(1,))
        t2 = threading.Thread(target=worker, args=(2,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert ref_counts[1] == 1, f"线程1引用计数应为1，实际为{ref_counts[1]}"
        assert ref_counts[2] == 1, f"线程2引用计数应为1，实际为{ref_counts[2]}"
