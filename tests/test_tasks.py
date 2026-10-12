def test_list_tasks_returns_registered_plugins(client):
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    tasks = [t["task"] for t in response.json()["tasks"]]
    assert "sentiment_analysis" in tasks
    assert "toxicity_detection" in tasks
