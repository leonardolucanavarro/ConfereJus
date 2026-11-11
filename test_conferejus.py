"""Testes locais: estrutura dos dados e recuperacao lexical, nao validacao juridica.

Execute na raiz do ConfereJus: uv run python test_conferejus.py
Nao consulta a internet, nao acessa secrets.toml e nao altera a base.
Os exemplos sao sinteticos e nao medem a qualidade em documentos reais.
"""

import csv
import io
import unittest
from datetime import date
from urllib.parse import urlparse
from unittest.mock import patch

import pandas as pd
from docx import Document
from pypdf import PdfWriter

from conferejus import analise as motor


def arquivo_em_memoria(nome, conteudo):
    arquivo = io.BytesIO(conteudo)
    arquivo.name = nome
    return arquivo


def acervo_ficticio():
    """Dados apenas para testar o codigo, nunca para integrar o acervo real."""
    temas = [
        ("TESTE001", "Mitigacao do prejuizo", "Medidas razoaveis para evitar o agravamento do prejuizo.", "mitigar, agravamento, prejuizo, medidas razoaveis"),
        ("TESTE002", "Multa compensatoria", "Multa compensatoria sobre obrigacoes pecuniarias solidarias.", "multa, compensatoria, obrigacoes, pecuniarias, solidariedade"),
        ("TESTE003", "Supressio e confianca legitima", "Inercia prolongada e cobranca retroativa afastada pela confianca legitima.", "supressio, confianca legitima, inercia, cobranca retroativa"),
    ]
    return pd.DataFrame([
        {"id": identificador, "processo": identificador, "tribunal": "TESTE",
         "orgao_julgador": "Orgao ficticio", "data_julgamento": "2020-01-01",
         "tema": tema, "tese_resumida": resumo, "palavras_chave": termos,
         "fonte_url": "https://example.invalid", "grau_autoridade": 1}
        for identificador, tema, resumo, termos in temas
    ])


class TestMotorIsolado(unittest.TestCase):
    """Verifica regras do programa usando um acervo ficticio em memoria."""

    def setUp(self):
        self.base = acervo_ficticio()
        substituicao = patch.object(motor, "carregar_jurisprudencias", return_value=self.base)
        substituicao.start()
        self.addCleanup(substituicao.stop)

    def analisar(self, texto, **opcoes):
        return motor.analisar_documento(texto, "Direito Contratual Empresarial", [], **opcoes)

    def test_01_mitigacao(self):
        resultado = self.analisar("Adotar medidas razoaveis para evitar o agravamento do prejuizo.")
        self.assertTrue(resultado)
        self.assertEqual(resultado[0]["id"], "TESTE001")

    def test_02_fora_do_escopo(self):
        self.assertEqual(self.analisar("Galaxias distantes possuem estrelas e planetas."), [])

    def test_03_metadados_nao_criam_resultados(self):
        resultado = motor.analisar_documento(
            "Galaxias distantes possuem estrelas e planetas.",
            "Mitigacao do prejuizo", ["multa compensatoria", "supressio"])
        self.assertEqual(resultado, [])

    def test_04_contexto_legado_nao_cria_resultados(self):
        self.assertEqual(self.analisar(
            "Galaxias distantes possuem estrelas e planetas.\n\nQuestao: nada"), [])
        self.assertEqual(self.analisar(
            "Galaxias distantes possuem estrelas e planetas.\n\nQuestão: multa compensatoria e supressio"), [])

    def test_05_trecho_citado_existe_no_original(self):
        trecho = "A inercia prolongada impede a cobranca retroativa pela confianca legitima."
        original = "Introducao sobre galaxias distantes.\n\n" + trecho
        resultado = self.analisar(original)
        self.assertTrue(resultado)
        self.assertEqual(resultado[0]["id"], "TESTE003")
        self.assertEqual(resultado[0]["trecho_relacionado"], trecho)
        self.assertIn(resultado[0]["trecho_relacionado"], original)

    def test_06_filtro_minimo_e_pontuacao(self):
        resultado = self.analisar("Multa compensatoria sobre obrigacoes pecuniarias solidarias.")
        self.assertTrue(resultado)
        for item in resultado:
            self.assertGreaterEqual(item["aderencia"], motor.LIMIAR_SIMILARIDADE)
            self.assertGreaterEqual(len(item["termos_relacionados"]), motor.MINIMO_TERMOS_COMUNS)
            self.assertGreaterEqual(item["aderencia"], 0)
            self.assertLessEqual(item["aderencia"], 1.0000001)
            self.assertEqual(item["aderencia_percentual"], round(item["aderencia"] * 100, 1))

    def test_07_ordem_e_limite(self):
        texto = "Medidas razoaveis para evitar o agravamento do prejuizo. Multa compensatoria sobre obrigacoes pecuniarias. Inercia prolongada e confianca legitima."
        resultado = self.analisar(texto)
        self.assertGreaterEqual(len(resultado), 2)
        self.assertEqual(resultado, sorted(resultado, key=lambda x: (-x["aderencia"], str(x["id"]))))
        self.assertEqual(self.analisar(texto, limite=1), resultado[:1])

    def test_08_data_e_autoridade_nao_alteram_ranking(self):
        texto = "Medidas razoaveis e agravamento do prejuizo. Multa compensatoria e obrigacoes pecuniarias."
        antes = [(x["id"], x["aderencia"]) for x in self.analisar(texto)]
        self.assertTrue(antes)
        self.base["data_julgamento"] = "2099-01-01"
        self.base["grau_autoridade"] = 999
        depois = [(x["id"], x["aderencia"]) for x in self.analisar(texto)]
        self.assertEqual(antes, depois)

    def test_09_normalizacao(self):
        self.assertEqual(motor.normalizar_texto("CLÁUSULA PENAL e inadimplemento"), "multa contratual e descumprimento")

    def test_10_negacao_preservada_nao_significa_interpretacao(self):
        self.assertIn("nao", motor._termos("Nao incide multa compensatoria"))
        resultado = self.analisar("Nao incide multa compensatoria sobre obrigacoes pecuniarias.")
        self.assertTrue(resultado)
        self.assertIn("opostas", resultado[0]["alerta"])

    def test_11_entrada_vazia(self):
        for texto in ("", "   ", None, 42):
            with self.subTest(texto=texto):
                self.assertEqual(self.analisar(texto), [])

    def test_12_limite_zero(self):
        self.assertEqual(self.analisar("Multa compensatoria", limite=0), [])

    def test_13_limite_de_caracteres(self):
        with self.assertRaises(ValueError):
            self.analisar("a" * (motor.MAXIMO_CARACTERES + 1))

    def test_14_limite_de_trechos(self):
        texto = "\n\n".join(["Multa compensatoria."] * (motor.MAXIMO_TRECHOS + 1))
        with self.assertRaises(ValueError):
            self.analisar(texto)

    def test_15_segmentacao_preserva_fim_do_texto(self):
        palavras = ["mitigacao", "prejuizo"] * 117 + ["encerramento"]
        original = " ".join(palavras)
        trechos = motor._segmentar(original)
        self.assertTrue(trechos)
        self.assertTrue(all(len(t.split()) <= 100 for t in trechos))
        self.assertTrue(all(t in original for t in trechos))
        self.assertTrue(trechos[-1].endswith(palavras[-1]))

    def test_16_nao_completa_lista_sem_correspondencia(self):
        resultado = self.analisar("Inercia prolongada e cobranca retroativa pela confianca legitima.")
        self.assertEqual([r["id"] for r in resultado], ["TESTE003"])

    def test_17_base_vazia(self):
        with patch.object(motor, "carregar_jurisprudencias", return_value=self.base.iloc[:0]):
            self.assertEqual(self.analisar("Multa compensatoria"), [])

    def test_18_vocabulario_inutil(self):
        for coluna in ("tema", "tese_resumida", "palavras_chave"):
            self.base[coluna] = "de a o contrato"
        self.assertEqual(self.analisar("Multa compensatoria"), [])


class TestArquivosEValidacao(unittest.TestCase):
    def test_19_txt_utf8_bom(self):
        arquivo = arquivo_em_memoria("teste.txt", "Confiança legítima".encode("utf-8-sig"))
        self.assertEqual(motor.extrair_texto_arquivo(arquivo), "Confiança legítima")

    def test_20_txt_latin1(self):
        arquivo = arquivo_em_memoria("teste.TXT", "Cláusula penal".encode("latin-1"))
        self.assertEqual(motor.extrair_texto_arquivo(arquivo), "Cláusula penal")

    def test_21_docx_paragrafo_e_tabela(self):
        documento = Document()
        documento.add_paragraph("Introducao do documento")
        documento.add_table(rows=1, cols=1).cell(0, 0).text = "Multa compensatoria"
        memoria = io.BytesIO()
        documento.save(memoria)
        texto = motor.extrair_texto_arquivo(arquivo_em_memoria("teste.docx", memoria.getvalue()))
        self.assertIn("Introducao do documento", texto)
        self.assertIn("Multa compensatoria", texto)

    def test_22_pdf_sem_texto(self):
        escritor = PdfWriter()
        escritor.add_blank_page(width=200, height=200)
        memoria = io.BytesIO()
        escritor.write(memoria)
        self.assertEqual(motor.extrair_texto_arquivo(arquivo_em_memoria("vazio.pdf", memoria.getvalue())), "")

    def test_23_formato_nao_aceito(self):
        with self.assertRaises(ValueError):
            motor.extrair_texto_arquivo(arquivo_em_memoria("imagem.png", b"imagem"))

    def test_24_arquivo_maior_que_limite(self):
        with self.assertRaises(ValueError):
            motor.extrair_texto_arquivo(arquivo_em_memoria("grande.txt", b"a" * (20 * 1024 * 1024 + 1)))

    def test_25_extracao_com_texto_longo_demais(self):
        with self.assertRaises(ValueError):
            motor.extrair_texto_arquivo(arquivo_em_memoria("longo.txt", b"a" * (motor.MAXIMO_CARACTERES + 1)))

    def test_26_csv_sem_coluna_obrigatoria(self):
        with patch.object(motor.pd, "read_csv", return_value=acervo_ficticio().drop(columns=["processo"])):
            with self.assertRaises(ValueError):
                motor.carregar_jurisprudencias()

    def test_27_csv_com_id_repetido(self):
        base = acervo_ficticio()
        base.loc[1, "id"] = base.loc[0, "id"]
        with patch.object(motor.pd, "read_csv", return_value=base):
            with self.assertRaises(ValueError):
                motor.carregar_jurisprudencias()


class TestBaseReal(unittest.TestCase):
    """Le o CSV do projeto. Nao testa vigencia, autenticidade ou teor juridico."""

    def test_28_colunas_alinhadas_e_campos_preenchidos(self):
        with motor.CAMINHO_BASE.open(encoding="utf-8-sig", newline="") as arquivo:
            linhas = list(csv.reader(arquivo, delimiter=";"))
        cabecalho = linhas[0]
        self.assertEqual(len(cabecalho), len(set(cabecalho)))
        obrigatorias = {"id", "tribunal", "processo", "orgao_julgador", "relator", "data_julgamento", "area", "tema", "tese_resumida", "palavras_chave", "grau_autoridade", "fonte_url", "contexto_origem", "limites_aplicacao"}
        self.assertTrue(obrigatorias.issubset(cabecalho))
        for numero, linha in enumerate(linhas[1:], 2):
            if not linha:
                continue
            with self.subTest(linha=numero):
                self.assertEqual(len(linha), len(cabecalho), "Colunas desalinhadas")
                self.assertTrue(all(campo.strip() for campo in linha), "Campo vazio")

    def test_29_acervo_minimo_e_identificadores(self):
        base = motor.carregar_jurisprudencias()
        self.assertGreaterEqual(len(base), 20)
        esperados = {f"J{i:03}" for i in range(1, 22) if i != 4}
        self.assertTrue(esperados.issubset(set(base["id"])))
        self.assertNotIn("J004", set(base["id"]), "Decisao retirada do escopo foi reintroduzida")
        self.assertFalse(base["processo"].duplicated().any())

    def test_30_datas_validas_e_dominios_oficiais(self):
        for registro in motor.carregar_jurisprudencias().to_dict(orient="records"):
            with self.subTest(id=registro["id"]):
                data = date.fromisoformat(str(registro["data_julgamento"]))
                self.assertLessEqual(data, date.today())
                endereco = urlparse(str(registro["fonte_url"]))
                host = (endereco.hostname or "").lower()
                self.assertEqual(endereco.scheme, "https")
                self.assertTrue(host == "stj.jus.br" or host.endswith(".stj.jus.br"))
                self.assertEqual(str(registro["tribunal"]), "STJ")

    def test_31_recuperacao_de_exemplos_sinteticos(self):
        exemplos = [
            ("J001", "O credor deve adotar medidas razoaveis para mitigar o agravamento do proprio prejuizo, conforme a boa-fe objetiva."),
            ("J011", "A empresa pede lucros cessantes com base em projecoes de rentabilidade de uma nova atividade empresarial que nao chegou a funcionar."),
            ("J012", "A contratante exigiu investimentos relevantes e depois promoveu a resilicao unilateral abrupta, sem prazo para reestruturacao da contratada."),
            ("J015", "O contrato de prestacao de servicos, os aditivos e os e-mails comprovam a probabilidade da divida para instruir acao monitoria com memoria de calculo."),
            ("J020", "O contrato de representacao comercial preve pagamento antecipado da indenizacao por rescisao injustificada junto com a remuneracao mensal do representante."),
        ]
        for esperado, texto in exemplos:
            with self.subTest(esperado=esperado):
                resultado = motor.analisar_documento(texto, "Direito Contratual Empresarial", [])
                self.assertIn(esperado, [r["id"] for r in resultado])

    def test_32_fora_do_escopo_com_acervo_real(self):
        texto = "Astronomos observaram galaxias distantes e estudaram a formacao de estrelas e planetas."
        self.assertEqual(motor.analisar_documento(texto, "Direito Contratual Empresarial", []), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
