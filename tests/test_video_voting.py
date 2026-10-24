from src.video_voting import VideoVoting


def test_ties_stay_unresolved_and_empty_frames_expire_old_results():
    voter = VideoVoting(10)
    assert voter.update("51F-123.45")["plate_text"] == "51F-123.45"
    assert voter.update("29A-1234")["plate_text"] is None
    assert voter.update("51F-123.45")["votes"] == 2
    for _ in range(10):
        result = voter.update(None)
    assert result["plate_text"] is None and result["votes"] == 0
    voter.reset()
    assert voter.update(None)["observations"] == 1
