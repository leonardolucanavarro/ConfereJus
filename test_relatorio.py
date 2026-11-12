"""Testes da exportacao em memoria. Nao usa rede, credenciais ou arquivos do usuario.

Execute: uv run python -m unittest test_relatorio -v
"""

import copy
import io
import unittest
import zipfile
from unittest.mock import patch

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT

from conferejus.relatorio import gerar_relatorio_docx


def revisao_ficticia():
    fonte = {
        "processo": "REsp 1.234.567/SP", "tribunal": "STJ", "orgao_julgador": "Turma de teste",
        "data_julgamento": "2020-01-01", "relator": "Relatoria fictícia", "tema": "Multa de teste",
        "aderencia_percentual": 23.1, "tese_resumida": "Síntese fictícia para testar a exportação.",
        "relacao_pedido": "Direção textual compatível", "explicacao_pedido": "Comparação textual de teste, sem conclusão jurídica.",
        "contexto_origem": "Contexto fictício preservado", "limites_aplicacao": "Limite fictício preservado",
        "trecho_relacionado": "A multa é excessiva.\nO pedido deve ser examinado.",
        "termos_relacionados": ["excessiva", "multa"], "justificativa": "Justificativa fictícia preservada",
        "explicacao_foco": "Foco fictício preservado", "alerta": "Alerta fictício preservado",
        "fonte_url": "https://processo.stj.jus.br/exemplo?teste=1&x=2",
    }
    referencia = {
        "citacao": "REsp 1.234.567/SP", "status": "Referência localizada na base",
        "tipo_correspondencia": "identificador_exato", "explicacao": "Identificador coincide, sem validar a transcrição.",
        "registros_base": [fonte], "quantidade": 1,
        "ocorrencias": [{"trecho": "Passagem original com REsp 1.234.567/SP."}],
        "aviso": "Não localizada não significa falsa.",
    }
    return {
        "objetivo": "Examinar a redução da multa", "tema": "Cláusula penal e multas",
        "posicao": "Devedora da obrigação discutida", "contexto": "Fato informado, sem verificação automática.",
        "gerado_em": "2026-11-12T18:30:00-03:00", "origem_documento": "contrato_teste.txt",
        "documento_sha256": "a" * 64, "caracteres_documento": 125,
        "resultados": [fonte], "referencias": [referencia], "erro_referencias": "",
    }


class TestRelatorio(unittest.TestCase):
    def setUp(self):
        self.revisao = revisao_ficticia()

    def gerar(self, revisao=None):
        dados = gerar_relatorio_docx(self.revisao if revisao is None else revisao)
        documento = Document(io.BytesIO(dados))
        texto = "\n".join(p.text for p in documento.paragraphs)
        return dados, documento, texto

    def test_01_docx_valido_em_bytes(self):
        dados, documento, _ = self.gerar()
        self.assertIsInstance(dados, bytes)
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(dados)))
        self.assertEqual(documento.paragraphs[0].style.name, "Title")
        self.assertFalse(documento.styles["Title"].element.xpath("./w:pPr/w:pBdr"))

    def test_02_objetivo_e_contexto_preservados(self):
        _, _, texto = self.gerar()
        for campo in ("objetivo", "tema", "posicao", "contexto"):
            self.assertIn(self.revisao[campo], texto)

    def test_03_metadados_e_fuso(self):
        _, _, texto = self.gerar()
        self.assertIn("12/11/2026 às 21:30 UTC", texto)
        self.assertIn("contrato_teste.txt", texto)
        self.assertIn("a" * 64, texto)
        self.assertIn("125", texto)

    def test_04_mesma_ordem_das_fontes(self):
        segunda = {**self.revisao["resultados"][0], "processo": "AREsp 9.876.543/RJ", "aderencia_percentual": 99.9}
        self.revisao["resultados"].append(segunda)
        _, _, texto = self.gerar()
        fontes = texto.split("Fontes sugeridas por assunto", 1)[1]
        self.assertLess(fontes.index("REsp 1.234.567/SP"), fontes.index("AREsp 9.876.543/RJ"))

    def test_05_trechos_e_explicacoes_preservados(self):
        _, _, texto = self.gerar()
        for campo in ("trecho_relacionado", "contexto_origem", "limites_aplicacao", "explicacao_pedido", "justificativa", "explicacao_foco", "alerta"):
            self.assertIn(self.revisao["resultados"][0][campo], texto)

    def test_06_percentual_nao_e_chance_de_exito(self):
        _, _, texto = self.gerar()
        self.assertIn("Similaridade textual: 23,1%", texto)
        self.assertIn("não representa probabilidade de êxito", texto)

    def test_07_status_distintos_sem_reinterpretacao(self):
        for status, tipo in (("Não verificada na base", "ausente"), ("Processo relacionado na base", "processo_relacionado"), ("Não verificada: referência incompleta", "incompleta")):
            with self.subTest(status=status):
                self.revisao["referencias"][0].update(status=status, tipo_correspondencia=tipo)
                self.assertIn(status, self.gerar()[2])

    def test_08_todas_ocorrencias_incluidas(self):
        self.revisao["referencias"][0]["ocorrencias"].append({"trecho": "Segunda passagem original."})
        _, _, texto = self.gerar()
        self.assertIn("Ocorrências no documento: 2", texto)
        self.assertIn("Segunda passagem original.", texto)

    def test_09_referencias_e_fontes_separadas(self):
        _, _, texto = self.gerar()
        self.assertLess(texto.index("Referências citadas no documento"), texto.index("Fontes sugeridas por assunto"))
        self.assertIn("independente da conferência", texto)

    def test_10_link_oficial_clicavel_sem_consulta(self):
        _, documento, _ = self.gerar()
        urls = [r.target_ref for r in documento.part.rels.values() if r.reltype == RT.HYPERLINK]
        self.assertIn(self.revisao["resultados"][0]["fonte_url"], urls)

    def test_11_link_inseguro_nao_exportado_como_hyperlink(self):
        for url in ("javascript:alert(1)", "file:///C:/privado", "https://stj.jus.br.evil.invalid/", "https://evil.invalid/stj.jus.br", "https://nome:senha@stj.jus.br", "https://stj.jus.br:9999/", "https://stj.jus.br/a b"):
            with self.subTest(url=url):
                self.revisao["resultados"][0]["fonte_url"] = url
                _, documento, texto = self.gerar()
                urls = [r.target_ref for r in documento.part.rels.values() if r.reltype == RT.HYPERLINK]
                self.assertNotIn(url, urls)
                self.assertIn("fora do domínio permitido", texto)

    def test_12_sem_resultados_nao_significa_ausencia_de_jurisprudencia(self):
        self.revisao["resultados"] = []
        _, _, texto = self.gerar()
        self.assertIn("Fontes sugeridas: 0", texto)
        self.assertIn("não significa que inexista jurisprudência", texto)

    def test_13_sem_referencias_nao_significa_sem_citacoes(self):
        self.revisao["referencias"] = []
        self.assertIn("não comprova que o documento esteja sem citações", self.gerar()[2])

    def test_14_erro_na_conferencia_nao_vira_resultado_negativo(self):
        self.revisao.update(referencias=[], erro_referencias="Limite de referências excedido.")
        texto = self.gerar()[2]
        self.assertIn("Conferência não concluída: Limite de referências excedido.", texto)
        self.assertNotIn("Nenhuma referência foi reconhecida", texto)

    def test_15_sem_login_credenciais_ou_documento_integral(self):
        self.revisao.update(email="privado@example.invalid", client_secret="SEGREDO_TESTE", documento="TEXTO_INTEGRAL_NAO_ANEXADO")
        dados, documento, texto = self.gerar()
        self.assertEqual(documento.core_properties.author, "ConfereJus")
        with zipfile.ZipFile(io.BytesIO(dados)) as pacote:
            xml = " ".join(pacote.read(n).decode("utf-8") for n in pacote.namelist() if n.endswith(".xml"))
        for valor in ("privado@example.invalid", "SEGREDO_TESTE", "TEXTO_INTEGRAL_NAO_ANEXADO"):
            self.assertNotIn(valor, xml)
        self.assertIn("Revise antes de compartilhar", texto)

    def test_16_nao_muta_a_revisao(self):
        antes = copy.deepcopy(self.revisao)
        self.gerar()
        self.assertEqual(self.revisao, antes)

    def test_17_campos_invalidos_e_hash_invalido(self):
        for valor in (None, {}, {"objetivo": "x", "resultados": "errado", "referencias": []}):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                gerar_relatorio_docx(valor)
        self.revisao["documento_sha256"] = "hash invalido"
        with self.assertRaises(ValueError):
            self.gerar()

    def test_18_data_invalida_ou_sem_fuso(self):
        for valor in ("data errada", "2026-11-12T18:30:00", 123):
            with self.subTest(valor=valor):
                self.revisao["gerado_em"] = valor
                with self.assertRaises(ValueError):
                    self.gerar()

    def test_19_xml_literal_controles_e_caminhos(self):
        self.revisao.update(objetivo="Ação <texto> & cláusula\x00", origem_documento=r"C:\Users\Privado\contrato.txt")
        _, _, texto = self.gerar()
        self.assertIn("Ação <texto> & cláusula\ufffd", texto)
        self.assertNotIn(r"C:\Users", texto)
        self.assertIn("contrato.txt", texto)

    def test_20_funciona_sem_campos_opcionais(self):
        _, _, texto = self.gerar({"objetivo": "Teste mínimo", "resultados": [], "referencias": []})
        self.assertIn("Teste mínimo", texto)
        self.assertIn("Fatos informados: Não informados", texto)
        self.assertIn("não é um parecer jurídico", texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
