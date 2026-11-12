"""Testes de regressao do contexto. Exemplos sinteticos, nao validacao juridica.

Execute na raiz: uv run python -m unittest test_conferejus test_contexto -v
Nao altera a base, nao consulta a internet e nao acessa credenciais.
"""

import unittest

from conferejus import analise as motor


TEXTO_REDUZIR = (
    "A contratada cumpriu parcialmente a obrigação. "
    "A multa compensatória cobrada é manifestamente excessiva diante da utilidade da prestação já recebida pela credora. "
    "Requer-se a redução equitativa da cláusula penal, considerando a natureza e a finalidade do negócio."
)
TEXTO_MANTER = (
    "A contratada cumpriu parcialmente a obrigação. "
    "A multa compensatória cobrada não é manifestamente excessiva diante da natureza e da finalidade do negócio. "
    "Requer-se a manutenção integral da cláusula penal, afastando sua redução equitativa."
)


class TestContexto(unittest.TestCase):
    def analisar(self, texto, objetivo="", **opcoes):
        return motor.analisar_documento(
            texto, "Direito Contratual Empresarial", [],
            objetivo=objetivo, **opcoes,
        )

    def test_01_reducao_prioriza_questao_especifica(self):
        resultado = self.analisar(TEXTO_REDUZIR, "Verificar os fundamentos para reduzir a multa contratual.")
        self.assertTrue(resultado)
        self.assertEqual(resultado[0]["id"], "J008")
        self.assertEqual(resultado[0]["relacao_pedido"], "Direção textual compatível")
        self.assertNotIn("J005", [r["id"] for r in resultado])
        self.assertNotIn("J021", [r["id"] for r in resultado])

    def test_02_pedido_oposto_nao_e_tratado_como_apoio(self):
        resultado = self.analisar(TEXTO_MANTER, "Verificar os fundamentos para manter integralmente a multa contratual.")
        registro = next(r for r in resultado if r["id"] == "J008")
        self.assertEqual(registro["relacao_pedido"], "Contraponto a conferir")
        self.assertIn("próprio contexto", registro["explicacao_pedido"])

    def test_03_objetivo_muda_ordem_sem_alterar_documento(self):
        reduzir = self.analisar(TEXTO_REDUZIR, "Reduzir a multa contratual")
        manter = self.analisar(TEXTO_REDUZIR, "Manter a multa contratual")
        self.assertEqual(reduzir[0]["id"], "J008")
        self.assertEqual(manter[0]["id"], "J007")
        self.assertEqual(manter[0]["relacao_pedido"], "Direção textual compatível")

    def test_04_percentual_nao_e_reescrito_como_nota_juridica(self):
        bruto = {r["id"]: r for r in motor.analisar_documento(TEXTO_REDUZIR, "", [], limite=30)}
        ordenado = self.analisar(TEXTO_REDUZIR, "Reduzir a multa contratual")
        for item in ordenado:
            self.assertEqual(item["aderencia"], bruto[item["id"]]["aderencia"])
            self.assertEqual(item["aderencia_percentual"], bruto[item["id"]]["aderencia_percentual"])

    def test_05_documento_fora_do_escopo_nao_ganha_fontes_por_contexto(self):
        resultado = self.analisar(
            "Astronomos estudam galaxias distantes, estrelas e planetas.",
            "Reduzir multa excessiva por cumprimento parcial",
            assunto="Cláusula penal e multas", posicao="Devedora da obrigação discutida",
            fatos="A multa excessiva viola a boa-fe objetiva.",
        )
        self.assertEqual(resultado, [])

    def test_06_posicao_nao_inventa_favorabilidade(self):
        credor = self.analisar(TEXTO_REDUZIR, "Reduzir multa contratual", posicao="Credora da obrigação discutida")
        devedor = self.analisar(TEXTO_REDUZIR, "Reduzir multa contratual", posicao="Devedora da obrigação discutida")
        campos = lambda resultado: [(r["id"], r["relacao_pedido"], r["pontuacao_ordenacao"]) for r in resultado]
        self.assertEqual(campos(credor), campos(devedor))

    def test_07_fatos_sem_ancora_nao_alteram_resultado(self):
        antes = self.analisar(TEXTO_REDUZIR, "Reduzir multa contratual")
        depois = self.analisar(TEXTO_REDUZIR, "Reduzir multa contratual", fatos="Galaxias planetas astronomia")
        self.assertEqual([r["id"] for r in antes], [r["id"] for r in depois])
        self.assertTrue(all(not r["fatos_usados_na_ordenacao"] for r in depois))

    def test_08_fatos_ancorados_tem_peso_declarado(self):
        resultado = self.analisar(TEXTO_REDUZIR, "Reduzir multa contratual", fatos="A multa excessiva deve considerar a utilidade da prestação.")
        self.assertTrue(resultado)
        self.assertTrue(all(r["fatos_usados_na_ordenacao"] for r in resultado))
        for registro in resultado:
            # Usa as afinidades arredondadas com tolerancia ao arredondamento.
            esperado = registro["aderencia"] * 0.65 + registro["afinidade_objetivo"] / 100 * 0.25 + registro["afinidade_fatos"] / 100 * 0.10
            self.assertAlmostEqual(registro["pontuacao_ordenacao"], esperado, delta=0.0002)

    def test_09_negacao_do_pedido_de_reducao(self):
        self.assertEqual(motor._sentido_pedido_multa("Não reduzir a multa contratual"), "manter")
        self.assertEqual(motor._sentido_pedido_multa("Afastar a redução da multa contratual"), "manter")

    def test_10_pedidos_mistos_nao_recebem_direcao_unica(self):
        self.assertEqual(motor._sentido_pedido_multa("Manter a multa ou, subsidiariamente, reduzir a multa"), "indefinido")

    def test_11_regras_nao_confundem_solidariedade_e_cumulacao(self):
        self.assertEqual(motor.identificar_questoes("Cláusula penal compensatória e obrigação pecuniária solidária"), {"multa_solidariedade"})
        self.assertEqual(motor.identificar_questoes("Multa compensatória e duplicidade de reparação por perdas e danos"), {"multa_cumulacao"})

    def test_12_solidariedade_continua_disponivel_quando_pertinente(self):
        resultado = self.analisar(
            "O devedor solidário assumiu a obrigação pecuniária de pagar a multa compensatória mesmo sem culpa pela entrega da embarcação.",
            "Conferir multa compensatória e solidariedade",
        )
        self.assertIn("J005", [r["id"] for r in resultado])

    def test_13_cumulacao_continua_disponivel_quando_pertinente(self):
        resultado = self.analisar(
            "A multa compensatória prefixa as perdas e danos e sua cumulação pode gerar duplicidade de reparação pelo mesmo inadimplemento.",
            "Conferir cumulação de multa e indenização",
        )
        self.assertIn("J021", [r["id"] for r in resultado])

    def test_14_contexto_e_limites_preservados(self):
        resultado = self.analisar(TEXTO_REDUZIR, "Reduzir multa contratual")
        self.assertTrue(resultado)
        for registro in resultado:
            self.assertTrue(registro["contexto_origem"])
            self.assertTrue(registro["limites_aplicacao"])
            self.assertTrue(registro["fonte_url"])

    def test_15_trecho_permanece_no_documento(self):
        for registro in self.analisar(TEXTO_REDUZIR, "Reduzir multa contratual"):
            self.assertIn(registro["trecho_relacionado"], TEXTO_REDUZIR)

    def test_16_criterios_antigos_nao_criam_resultados(self):
        resultado = motor.analisar_documento("Galaxias estrelas planetas.", "Multa contratual", ["reducao equitativa"])
        self.assertEqual(resultado, [])

    def test_17_limite_e_entrada_vazia_preservados(self):
        self.assertEqual(self.analisar("", "Reduzir multa contratual"), [])
        self.assertEqual(self.analisar(TEXTO_REDUZIR, "Reduzir multa contratual", limite=0), [])
        self.assertLessEqual(len(self.analisar(TEXTO_REDUZIR, "Reduzir multa contratual", limite=1)), 1)

    def test_18_objetivo_inconsistente_nao_completa_lista(self):
        self.assertEqual(self.analisar(
            "A multa compensatória cobrada é manifestamente excessiva e deve ser reduzida.",
            "Conferir a obrigação de mitigar o agravamento do prejuízo",
        ), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
