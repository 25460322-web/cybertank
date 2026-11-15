import json

import pytest

import server


@pytest.fixture(autouse=True)
def arena_vacia():
    server.estado.clear()
    server.balas.clear()
    server.ult_disparo.clear()
    yield


def test_snapshot_incluye_a_los_jugadores():
    server.estado["ana"] = {"id": "ana", "x": 1.0, "y": 2.0}
    assert json.loads(server.snapshot())["e"]["ana"]["x"] == 1.0


def test_partida_es_5_vs_5():
    assert server.MAX_JUGADORES == 10


def test_la_posicion_no_sale_de_la_arena():
    server.procesar_entrada({"id": "ana", "x": -500, "y": 99999})
    t = server.estado["ana"]
    assert t["x"] == server.RADIO_TANQUE
    assert t["y"] == server.ALTO - server.RADIO_TANQUE


def test_disparar_crea_una_bala_y_respeta_la_cadencia():
    server.procesar_entrada({"id": "ana", "x": 100, "y": 100, "a": 0, "dispara": True}, ahora=10.0)
    server.procesar_entrada({"id": "ana", "x": 100, "y": 100, "a": 0, "dispara": True}, ahora=10.1)
    assert len(server.balas) == 1
    server.procesar_entrada({"id": "ana", "x": 100, "y": 100, "a": 0, "dispara": True}, ahora=10.5)
    assert len(server.balas) == 2


def test_cuatro_impactos_destruyen_al_tanque_y_dan_puntos():
    server.procesar_entrada({"id": "ana", "x": 100, "y": 400, "a": 0})
    server.procesar_entrada({"id": "beto", "x": 200, "y": 400})
    for i in range(4):
        server.procesar_entrada({"id": "ana", "a": 0, "dispara": True}, ahora=100.0 + i)
        derribos = []
        for _ in range(10):
            derribos += server.avanzar(0.02)
    beto, ana = server.estado["beto"], server.estado["ana"]
    assert derribos == [("ana", "beto")]
    assert ana["puntos"] == server.PUNTOS_DERRIBO
    assert beto["vida"] == server.VIDA_MAX and beto["muertes"] == 1 and beto["spawn"] == 1


def test_la_posicion_vieja_se_ignora_tras_reaparecer():
    server.procesar_entrada({"id": "beto", "x": 200, "y": 400})
    server.reaparecer(server.estado["beto"])
    nueva = (server.estado["beto"]["x"], server.estado["beto"]["y"])
    server.procesar_entrada({"id": "beto", "x": 200, "y": 400, "spawn": 0})
    assert (server.estado["beto"]["x"], server.estado["beto"]["y"]) == nueva


def test_las_balas_desaparecen_al_salir_de_la_arena():
    server.procesar_entrada({"id": "ana", "x": 1170, "y": 400, "a": 0, "dispara": True})
    server.avanzar(0.5)
    assert server.balas == []
