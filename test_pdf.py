"""Regressao da extracao de PDF, com documentos sinteticos em memoria.

Nao usa rede, OCR, dados pessoais ou arquivos externos.
Execute: uv run python -m unittest test_pdf -v
"""

import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from conferejus import analise as motor


TEXTO = (
    "A contratada cumpriu parcialmente a obrigação. A multa contratual cobrada é "
    "manifestamente excessiva diante da utilidade da prestação já recebida pela credora. "
    "Requer-se a redução equitativa da cláusula penal. A parte cita o REsp 1.447.247/SP."
)


def arquivo(nome, conteudo):
    memoria = io.BytesIO(conteudo)
    memoria.name = nome
    return memoria


def pagina_simulada(padrao, layout):
    pagina = Mock()
    pagina.extract_text.side_effect = lambda **opcoes: layout if opcoes else padrao
    return pagina


def pdf_fragmentado(texto=TEXTO):
    """Texto vetorial com objetos separados para palavras e espacos.

    Matrizes invertidas reproduzem o comportamento observado no PDF de teste.
    Usa fonte padrao do PDF, sem fonte de terceiros ou dependencia adicional.
    """
    escritor = PdfWriter()
    pagina = escritor.add_blank_page(width=595, height=842)
    fonte = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"), NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })
    pagina[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): escritor._add_object(fonte)}),
    })
    operacoes = ["1 0 0 -1 0 842 cm", "q", ".75 0 0 .75 72 72 cm"]
    x, y = 0, -15
    for palavra in texto.split():
        if x + len(palavra) * 7 > 650:
            x, y = 0, y - 20
        literal = palavra.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")
        operacoes.append(f"BT /F1 12 Tf 1 0 0 -1 0 0.48 Tm {x} {y} Td ({literal}) Tj ET")
        x += len(palavra) * 7
        operacoes.append(f"BT /F1 12 Tf 1 0 0 -1 0 0.48 Tm {x} {y} Td ( ) Tj ET")
        x += 6
    operacoes.append("Q")
    fluxo = DecodedStreamObject()
    fluxo.set_data("\n".join(operacoes).encode("cp1252"))
    pagina[NameObject("/Contents")] = escritor._add_object(fluxo)
    memoria = io.BytesIO()
    escritor.write(memoria)
    return memoria.getvalue()


def base_ficticia():
    return pd.DataFrame([{
        "id": "FICTICIO_PDF", "tribunal": "STJ", "processo": "REsp 1.234.567/SP",
        "orgao_julgador": "Turma fictícia", "data_julgamento": "2020-01-01",
        "tema": "Redução de ofício de cláusula penal manifestamente excessiva",
        "tese_resumida": "A multa contratual manifestamente excessiva deve reduzir seu valor por redução equitativa.",
        "palavras_chave": "multa, excessiva, redução equitativa, cláusula penal",
        "fonte_url": "https://example.invalid", "contexto_origem": "Dados de teste", "limites_aplicacao": "Não usar como fonte jurídica",
    }])


class TestPDF(unittest.TestCase):
    def setUp(self):
        self.fragmentado = "\n \n".join(TEXTO.split())

    def test_01_detecta_fragmentacao_por_palavras(self):
        self.assertTrue(motor._pdf_texto_fragmentado(self.fragmentado))
        self.assertTrue(motor._pdf_texto_fragmentado("\n".join(TEXTO.split())))

    def test_02_nao_confunde_paragrafos_comuns(self):
        self.assertFalse(motor._pdf_texto_fragmentado(TEXTO))
        self.assertFalse(motor._pdf_texto_fragmentado("Título\n\n" + TEXTO + "\n\n" + TEXTO))

    def test_03_extracao_comum_permanece_identica(self):
        pagina = pagina_simulada(TEXTO, "não usar")
        self.assertEqual(motor._extrair_texto_pagina_pdf(pagina), TEXTO)
        pagina.extract_text.assert_called_once_with()

    def test_04_pagina_vazia_nao_inventa_texto(self):
        pagina = pagina_simulada(None, "não usar")
        self.assertEqual(motor._extrair_texto_pagina_pdf(pagina), "")
        pagina.extract_text.assert_called_once_with()

    def test_05_layout_preserva_palavras_e_reconstitui_linhas(self):
        for layout in (TEXTO, TEXTO.replace(" ", "   ").replace("cláusula   penal", "cláusula\npenal")):
            with self.subTest(layout=layout):
                pagina = pagina_simulada(self.fragmentado, layout)
                self.assertEqual(motor._extrair_texto_pagina_pdf(pagina), TEXTO)
                self.assertEqual(pagina.extract_text.call_count, 2)
                pagina.extract_text.assert_called_with(extraction_mode="layout")

    def test_06_layout_ainda_fragmentado_nao_substitui(self):
        pagina = pagina_simulada(self.fragmentado, self.fragmentado)
        self.assertEqual(motor._extrair_texto_pagina_pdf(pagina), self.fragmentado)

    def test_07_nao_aceita_palavra_removida(self):
        pagina = pagina_simulada(self.fragmentado, TEXTO.replace("manifestamente ", ""))
        self.assertEqual(motor._extrair_texto_pagina_pdf(pagina), self.fragmentado)

    def test_08_nao_aceita_palavra_acrescentada(self):
        pagina = pagina_simulada(self.fragmentado, TEXTO + " Outra palavra.")
        self.assertEqual(motor._extrair_texto_pagina_pdf(pagina), self.fragmentado)

    def test_09_nao_aceita_mudanca_de_ordem(self):
        pagina = pagina_simulada(self.fragmentado, " ".join(reversed(TEXTO.split())))
        self.assertEqual(motor._extrair_texto_pagina_pdf(pagina), self.fragmentado)

    def test_10_negacao_nao_e_apagada(self):
        original = TEXTO.replace("é manifestamente", "não é manifestamente")
        fragmentado = "\n\n".join(original.split())
        pagina = pagina_simulada(fragmentado, TEXTO)
        self.assertEqual(motor._extrair_texto_pagina_pdf(pagina), fragmentado)

    def test_11_modo_indisponivel_preserva_padrao(self):
        for erro in (TypeError("modo indisponível"), ValueError("layout inválido"), NotImplementedError()):
            with self.subTest(erro=type(erro).__name__):
                pagina = Mock()
                pagina.extract_text.side_effect = [self.fragmentado, erro]
                self.assertEqual(motor._extrair_texto_pagina_pdf(pagina), self.fragmentado)

    def test_12_layout_vazio_nao_apaga_o_texto(self):
        self.assertEqual(motor._extrair_texto_pagina_pdf(pagina_simulada(self.fragmentado, "")), self.fragmentado)

    def test_13_pdf_vetorial_real_em_memoria(self):
        dados = pdf_fragmentado()
        bruto = PdfReader(io.BytesIO(dados)).pages[0].extract_text()
        self.assertTrue(motor._pdf_texto_fragmentado(bruto))
        self.assertEqual(motor._segmentar(bruto), [])
        corrigido = motor.extrair_texto_arquivo(arquivo("teste.pdf", dados))
        self.assertEqual(corrigido.split(), TEXTO.split())
        self.assertTrue(motor._segmentar(corrigido))

    def test_14_recuperacao_pdf_equivale_ao_texto(self):
        texto = motor.extrair_texto_arquivo(arquivo("teste.pdf", pdf_fragmentado()))
        with patch.object(motor, "carregar_jurisprudencias", return_value=base_ficticia()):
            opcoes = {"objetivo": "Examinar o pedido de redução da multa contratual.", "assunto": "Cláusula penal e multas"}
            do_pdf = motor.analisar_documento(texto, "", [], **opcoes)
            do_texto = motor.analisar_documento(TEXTO, "", [], **opcoes)
        self.assertTrue(do_pdf)
        self.assertEqual([r["id"] for r in do_pdf], [r["id"] for r in do_texto])
        self.assertEqual(do_pdf[0]["aderencia_percentual"], do_texto[0]["aderencia_percentual"])
        self.assertIn(do_pdf[0]["trecho_relacionado"], texto)

    def test_15_pdf_fora_do_escopo_nao_ganha_fontes(self):
        texto = "Os astrônomos estudam galáxias distantes e observam estrelas planetas nebulosas e telescópios espaciais."
        extraido = motor.extrair_texto_arquivo(arquivo("astronomia.pdf", pdf_fragmentado(texto)))
        with patch.object(motor, "carregar_jurisprudencias", return_value=base_ficticia()):
            self.assertEqual(motor.analisar_documento(extraido, "", [], objetivo="Reduzir multa contratual"), [])

    def test_16_ordem_e_separacao_de_paginas_preservadas(self):
        leitor = SimpleNamespace(pages=[pagina_simulada("Primeira página normal.", ""), pagina_simulada(self.fragmentado, TEXTO)])
        with patch.object(motor, "PdfReader", return_value=leitor):
            texto = motor.extrair_texto_arquivo(arquivo("duas.pdf", b"simulado"))
        self.assertEqual(texto, "Primeira página normal.\n\n" + TEXTO)

    def test_17_limites_de_paginas_e_caracteres(self):
        leitor = SimpleNamespace(pages=[Mock()] * 201)
        with patch.object(motor, "PdfReader", return_value=leitor), self.assertRaisesRegex(ValueError, "200"):
            motor.extrair_texto_arquivo(arquivo("grande.pdf", b"simulado"))
        pagina = pagina_simulada("a" * (motor.MAXIMO_CARACTERES + 1), "")
        with patch.object(motor, "PdfReader", return_value=SimpleNamespace(pages=[pagina])), self.assertRaisesRegex(ValueError, "120 mil"):
            motor.extrair_texto_arquivo(arquivo("longo.pdf", b"simulado"))

    def test_18_txt_nao_e_reformatado_pela_correcao_pdf(self):
        texto = motor.extrair_texto_arquivo(arquivo("teste.txt", self.fragmentado.encode("utf-8")))
        self.assertEqual(texto, self.fragmentado.strip())

    def test_19_extensao_pdf_em_maiusculas(self):
        texto = motor.extrair_texto_arquivo(arquivo("teste.PDF", pdf_fragmentado()))
        self.assertEqual(texto.split(), TEXTO.split())

    def test_20_referencia_citada_permanece_identica(self):
        texto = motor.extrair_texto_arquivo(arquivo("teste.pdf", pdf_fragmentado()))
        referencias = motor.extrair_referencias(texto)
        self.assertEqual(len(referencias), 1)
        self.assertEqual(referencias[0]["numero"], "1447247")
        self.assertEqual(referencias[0]["uf"], "SP")
        self.assertIn(referencias[0]["citacao"], texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
