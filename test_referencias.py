"""Conferencia local de identificadores; nao certifica decisoes ou transcricoes.

Execute: uv run python -m unittest test_referencias -v
Acervo ficticio em memoria. Sem rede, credenciais ou escrita na base.
"""

import unittest
from unittest.mock import patch

import pandas as pd

from conferejus import analise as motor


class TestReferencias(unittest.TestCase):
    def setUp(self):
        self.base = pd.DataFrame([
            {"id": "FICTICIO_A", "tribunal": "STJ", "processo": "REsp 1.234.567/SP", "fonte_url": "https://example.invalid/a"},
            {"id": "FICTICIO_B", "tribunal": "STJ", "processo": "AgInt no AREsp 2.345.678/AM", "fonte_url": "https://example.invalid/b"},
            {"id": "FICTICIO_C", "tribunal": "STJ", "processo": "REsp 1.234.567/RJ", "fonte_url": "https://example.invalid/c"},
            {"id": "FICTICIO_D", "tribunal": "OUTRO", "processo": "REsp 9.876.543/DF", "fonte_url": "https://example.invalid/d"},
        ])
        simulacao = patch.object(motor, "carregar_jurisprudencias", return_value=self.base)
        self.carregar = simulacao.start()
        self.addCleanup(simulacao.stop)

    def conferir(self, texto):
        return motor.conferir_referencias(texto)[0]

    def test_01_identificador_exato(self):
        r = self.conferir("Conforme o REsp 1.234.567/SP, citado pela parte.")
        self.assertEqual(r["tipo_correspondencia"], "identificador_exato")
        self.assertEqual(r["registros_base"][0]["id"], "FICTICIO_A")

    def test_02_numero_sem_pontos_e_caixa(self):
        self.assertEqual(self.conferir("resp 1234567/sp")["tipo_correspondencia"], "identificador_exato")

    def test_03_marcadores_numero_e_espacos(self):
        for texto in ("REsp nº 1.234.567 / SP", "REsp n. 1234567/SP", "REsp número 1234567/SP", "REsp N.º 1234567/SP"):
            with self.subTest(texto=texto):
                self.assertEqual(self.conferir(texto)["tipo_correspondencia"], "identificador_exato")

    def test_04_incidente_exato(self):
        self.assertEqual(self.conferir("AgInt no AREsp 2.345.678/AM")["tipo_correspondencia"], "identificador_exato")

    def test_05_incidente_nao_e_recurso_principal(self):
        r = self.conferir("AREsp 2.345.678/AM")
        self.assertEqual(r["tipo_correspondencia"], "processo_relacionado")
        self.assertIn("Não foi localizada a referência exata", r["explicacao"])

    def test_06_incidente_acrescentado_nao_e_exato(self):
        self.assertEqual(self.conferir("AgInt no REsp 1.234.567/SP")["tipo_correspondencia"], "processo_relacionado")

    def test_07_incidentes_encadeados_preservados(self):
        r = self.conferir("EDcl no AgInt no AREsp 2.345.678/AM")
        self.assertEqual(r["incidentes"], ["EDcl", "AgInt"])
        self.assertEqual(r["tipo_correspondencia"], "processo_relacionado")

    def test_08_classe_diferente_nao_coincide(self):
        self.assertEqual(self.conferir("AREsp 1.234.567/SP")["tipo_correspondencia"], "ausente")

    def test_09_uf_diferente_nao_coincide(self):
        r = self.conferir("REsp 1.234.567/MG")
        self.assertEqual(r["tipo_correspondencia"], "ausente")
        self.assertEqual(r["registros_base"], [])
        self.assertIn("UF diferente", r["explicacao"])

    def test_10_uf_ausente_nao_inferida(self):
        r = self.conferir("REsp 1.234.567")
        self.assertEqual(r["tipo_correspondencia"], "incompleta")
        self.assertEqual(r["uf"], "")
        self.assertEqual(r["registros_base"], [])

    def test_11_uf_invalida(self):
        self.assertEqual(self.conferir("REsp 1.234.567/ZZ")["tipo_correspondencia"], "uf_invalida")

    def test_12_ausente_nao_significa_falso(self):
        r = self.conferir("REsp 9.999.999/DF")
        self.assertEqual(r["status"], "Não verificada na base")
        self.assertIn("não se pode concluir", r["explicacao"])

    def test_13_repeticoes_agrupadas(self):
        resultado = motor.conferir_referencias("REsp 1.234.567/SP e resp 1234567/sp")
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["quantidade"], 2)

    def test_14_trechos_e_posicoes_sao_originais(self):
        original = "Ação com acentuação: REsp nº 1.234.567 / SP. Outra passagem."
        for r in motor.extrair_referencias(original):
            for ocorrencia in r["ocorrencias"]:
                self.assertEqual(original[ocorrencia["inicio"]:ocorrencia["fim"]], ocorrencia["citacao"])
                self.assertIn(ocorrencia["trecho"], original)

    def test_15_sem_citacao_nao_carrega_base(self):
        self.assertEqual(motor.conferir_referencias("Galáxias e estrelas."), [])
        self.carregar.assert_not_called()

    def test_16_numero_ou_artigo_sozinho_nao_e_citacao(self):
        self.assertEqual(motor.extrair_referencias("Art. 413. Dívida de 1.234.567 reais. Processo 1234567/SP."), [])

    def test_17_contexto_legado_nao_cria_citacao(self):
        self.assertEqual(motor.conferir_referencias("Texto sem referência.\n\nQuestão: REsp 1.234.567/SP"), [])

    def test_18_outro_tribunal_na_base_nao_e_stj(self):
        self.assertEqual(self.conferir("REsp 9.876.543/DF")["tipo_correspondencia"], "ausente")

    def test_19_base_vazia(self):
        self.carregar.return_value = self.base.iloc[:0]
        self.assertEqual(self.conferir("REsp 1.234.567/SP")["tipo_correspondencia"], "ausente")

    def test_20_cadastro_ambiguo_nao_e_exato(self):
        self.carregar.return_value = pd.concat([self.base, self.base.iloc[:1]], ignore_index=True)
        self.assertEqual(self.conferir("REsp 1.234.567/SP")["tipo_correspondencia"], "ambigua")

    def test_21_vazio_tipo_e_limite(self):
        self.assertEqual(motor.conferir_referencias(""), [])
        with self.assertRaises(ValueError):
            motor.conferir_referencias(None)
        with self.assertRaises(ValueError):
            motor.conferir_referencias("a" * (motor.MAXIMO_CARACTERES + 1))

    def test_22_avisos_e_link_vem_da_base(self):
        r = self.conferir("REsp 1.234.567/SP")
        self.assertEqual(r["registros_base"][0]["fonte_url"], "https://example.invalid/a")
        self.assertIn("teor da citação", r["aviso"])
        self.assertIn("Não localizada não significa falsa", r["aviso"])

    def test_23_multiplas_referencias_ordem_original(self):
        resultado = motor.conferir_referencias("REsp 9.999.999/DF e AgInt no AREsp 2.345.678/AM e REsp 1.234.567/SP")
        self.assertEqual([r["tipo_correspondencia"] for r in resultado], ["ausente", "identificador_exato", "identificador_exato"])

    def test_24_incompletas_nao_se_fundem_com_completas(self):
        resultado = motor.conferir_referencias("REsp 1.234.567 e REsp 1.234.567/SP")
        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0]["tipo_correspondencia"], "incompleta")
        self.assertEqual(resultado[1]["tipo_correspondencia"], "identificador_exato")

    def test_25_limite_de_referencias_sem_truncamento_silencioso(self):
        texto = "; ".join(f"REsp {i}/SP" for i in range(1, motor.MAXIMO_REFERENCIAS + 2))
        with self.assertRaises(ValueError):
            motor.conferir_referencias(texto)

    def test_26_nao_altera_o_acervo(self):
        antes = self.base.copy(deep=True)
        motor.conferir_referencias("REsp 1.234.567/SP")
        pd.testing.assert_frame_equal(self.base, antes)

    def test_27_numeros_malformados_nao_viram_identificadores_parciais(self):
        for texto in ("REsp 1.23/SP", "REsp 1.234.5678/SP", "REsp 1234567/SPX", "REsp 1234567/2020"):
            with self.subTest(texto=texto):
                self.assertEqual(motor.extrair_referencias(texto), [])

    def test_28_limites_de_palavra(self):
        self.assertEqual(motor.extrair_referencias("outroREsp 1.234.567/SP e EAREsp 2.345.678/AM"), [])

    def test_29_base_nao_deduzida_do_argumento(self):
        self.assertEqual(motor.conferir_referencias("A multa deve ser reduzida, segundo o STJ."), [])

    def test_30_exata_nao_confirma_afirmacao_atribuida(self):
        r = self.conferir("O REsp 1.234.567/SP afirma que qualquer multa é sempre válida.")
        self.assertEqual(r["tipo_correspondencia"], "identificador_exato")
        self.assertIn("não verifica o conteúdo", r["explicacao"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
