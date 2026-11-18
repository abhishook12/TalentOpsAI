from scout_desktop.sync.local_queue import LocalQueue


def test_pending_record_is_not_displayed_as_cloud_verified():
    queue = LocalQueue(":memory:")
    queue_id = queue.enqueue_cluster({
        "canonical_name": "Morgan Reed",
        "recruiter_name": "Morgan Reed",
        "title": "Senior Recruiter",
        "company_name": "Acme Corp",
        "source_url": "https://www.linkedin.com/in/morgan-reed",
        "canonical_profile_url": "https://www.linkedin.com/in/morgan-reed",
        "entity_type": "PERSON",
        "platform": "LINKEDIN",
    })

    assert queue.get_recent_candidates()[0]["status"] == "QUEUED"
    queue.mark_batch_synced([queue_id])
    assert queue.get_recent_candidates()[0]["status"] == "VERIFIED"
    queue.close()


def test_pipeline_stages_do_not_exceed_their_previous_stage():
    queue = LocalQueue(":memory:")
    for number in range(2):
        queue.enqueue_cluster({
            "canonical_name": f"Person {number}",
            "recruiter_name": f"Person {number}",
            "company_name": "Acme Corp",
            "source_url": f"https://www.linkedin.com/in/person-{number}",
        })
    summary = queue.get_pipeline_summary_stats()
    assert summary["canonical"] <= summary["validated"] <= summary["understood"] <= summary["observed"]
    queue.close()
