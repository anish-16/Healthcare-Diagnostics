"""Catalogue browsing: centres, tests, per-centre prices."""


def test_list_centres(client, catalogue):
    res = client.get("/api/centres")
    assert res.status_code == 200
    names = [c["name"] for c in res.json()]
    assert "CityCare Diagnostics" in names


def test_get_centre(client, catalogue):
    res = client.get(f"/api/centres/{catalogue['centre'].id}")
    assert res.status_code == 200
    assert res.json()["location"] == "MG Road, Pune"


def test_get_missing_centre(client):
    assert client.get("/api/centres/9999").status_code == 404


def test_centre_tests_show_per_centre_prices(client, catalogue):
    res = client.get(f"/api/centres/{catalogue['centre'].id}/tests")
    assert res.status_code == 200
    tests = res.json()["tests"]
    prices = {t["test_id"]: t["price"] for t in tests}
    assert prices[catalogue["tests"][0].id] == "299.00"
    assert prices[catalogue["tests"][1].id] == "899.00"


def test_list_tests(client, catalogue):
    res = client.get("/api/tests")
    assert res.status_code == 200
    assert {t["name"] for t in res.json()} >= {"CBC", "Lipid Profile"}


def test_get_missing_test(client):
    assert client.get("/api/tests/9999").status_code == 404


def test_test_offerings_endpoint(client, catalogue):
    res = client.get(f"/api/tests/{catalogue['tests'][0].id}/offerings")
    assert res.status_code == 200
    assert res.json()[0]["price"] == "299.00"
