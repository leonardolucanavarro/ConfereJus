"""30 testes de assunto e preparacao da leitura. Exemplos sinteticos.

Nao consulta a internet, nao le credenciais e nao grava arquivos.
Execute: uv run python -m unittest test_assunto -v
"""

import io
import unittest
import unicodedata
from hashlib import sha256
from unittest.mock import patch

from docx import Document
from pypdf import PdfWriter

from conferejus import analise as motor


TEXTO_MULTA = "A multa contratual é excessiva. Requer-se redução da cláusula penal. A parte cita o REsp 1.447.247/SP."


def arquivo(nome, dados):
    memoria = io.BytesIO(dados)
    memoria.name = nome
    return memoria


class TestAssunto(unittest.TestCase):
    def sugerido(self, texto):
        return motor.sugerir_assunto(texto)["assunto"]

    def test_01_clausula_penal(self):
        self.assertEqual(self.sugerido(TEXTO_MULTA), "Cláusula penal e multas")

    def test_02_multa_plural_e_compensatoria(self):
        for texto in ("Multas contratuais", "Multa compensatória", "Cláusulas penais", "Penalidades contratuais"):
            with self.subTest(texto=texto):
                self.assertEqual(self.sugerido(texto), "Cláusula penal e multas")

    def test_03_boafe_supressio(self):
        self.assertEqual(self.sugerido("Supressio e confiança legítima pela boa-fé objetiva."), "Boa-fé e comportamento das partes")

    def test_04_mitigacao(self):
        self.assertEqual(self.sugerido("Duty to mitigate the loss e agravamento do prejuízo."), "Boa-fé e comportamento das partes")

    def test_05_revisao(self):
        self.assertEqual(self.sugerido("Revisão contratual por onerosidade excessiva e teoria da imprevisão."), "Revisão contratual")

    def test_06_perdas_e_danos(self):
        self.assertEqual(self.sugerido("Perdas e danos, lucros cessantes e danos emergentes."), "Perdas e danos")

    def test_07_inadimplemento(self):
        self.assertEqual(self.sugerido("Inadimplemento e resolução contratual."), "Inadimplemento e resolução contratual")

    def test_08_adimplemento_substancial_e_excecao(self):
        for texto in ("Adimplemento substancial", "Exceção do contrato não cumprido", "Resilição e denúncia imotivada"):
            with self.subTest(texto=texto):
                self.assertEqual(self.sugerido(texto), "Inadimplemento e resolução contratual")

    def test_09_termos_genericos_nao_forcam_categoria(self):
        self.assertEqual(self.sugerido("Contrato entre partes, direito e prestação de serviços."), motor.OPCOES_ASSUNTOS[-1])

    def test_10_astronomia_nao_e_contrato(self):
        resultado = motor.sugerir_assunto("Galáxias estrelas planetas e telescópios.")
        self.assertEqual(resultado["situacao"], "nao_identificado")
        self.assertEqual(resultado["evidencias"], [])

    def test_11_multiplos_assuntos_sem_forcar_escolha(self):
        resultado = motor.sugerir_assunto("Cláusula penal e lucros cessantes.")
        self.assertEqual(resultado["situacao"], "multiplos")
        self.assertEqual(resultado["assunto"], motor.OPCOES_ASSUNTOS[-1])
        self.assertEqual(set(resultado["assuntos_detectados"]), {"Cláusula penal e multas", "Perdas e danos"})

    def test_12_predominancia_declarada_e_indicadores_secundarios(self):
        resultado = motor.sugerir_assunto("Multa contratual e cláusula penal. Há menção à boa-fé objetiva.")
        self.assertEqual(resultado["assunto"], "Cláusula penal e multas")
        self.assertIn("Boa-fé e comportamento das partes", resultado["assuntos_detectados"])

    def test_13_repeticao_nao_muda_peso(self):
        a = motor.sugerir_assunto("Multa contratual. Lucros cessantes.")
        b = motor.sugerir_assunto("Multa contratual. " * 20 + "Lucros cessantes.")
        self.assertEqual(a["indicadores_por_assunto"], b["indicadores_por_assunto"])
        self.assertEqual(a["assunto"], b["assunto"])

    def test_14_contexto_legado_nao_inventa_tema(self):
        self.assertEqual(self.sugerido("Galáxias e estrelas.\n\nQuestão: reduzir multa contratual e cláusula penal"), motor.OPCOES_ASSUNTOS[-1])

    def test_15_identificador_citado_nao_deduz_assunto(self):
        self.assertEqual(self.sugerido("REsp 1.447.247/SP e AgInt no AREsp 1.738.129/AM."), motor.OPCOES_ASSUNTOS[-1])

    def test_16_evidencias_e_posicoes_existem_no_original(self):
        for original in ("Ação sobre CLÁUSULA PENAL e boa-fé.", unicodedata.normalize("NFD", "Cláusula penal e boa-fé.")):
            with self.subTest(original=original):
                for evidencia in motor.sugerir_assunto(original)["evidencias"]:
                    self.assertEqual(original[evidencia["inicio"]:evidencia["fim"]], evidencia["expressao"])
                    self.assertIn(evidencia["trecho"], original)

    def test_17_expressoes_atravessam_quebras_visuais(self):
        self.assertEqual(self.sugerido("CLÁUSULA\nPENAL e multa   contratual."), "Cláusula penal e multas")

    def test_18_vazio_tipo_e_limite(self):
        self.assertEqual(motor.sugerir_assunto("")["situacao"], "nao_identificado")
        for texto in (None, "a" * (motor.MAXIMO_CARACTERES + 1)):
            with self.subTest(texto=type(texto).__name__), self.assertRaises(ValueError):
                motor.sugerir_assunto(texto)

    def test_19_somente_opcoes_existentes_sem_confianca_fabricada(self):
        self.assertEqual(len(motor.OPCOES_ASSUNTOS), 6)
        resultado = motor.sugerir_assunto(TEXTO_MULTA)
        self.assertIn(resultado["assunto"], motor.OPCOES_ASSUNTOS)
        self.assertNotIn("confianca", resultado)
        self.assertNotIn("percentual", resultado)
        self.assertIn("não interpreta", resultado["aviso"])

    def test_20_nao_consulta_base_e_nao_classifica_sentido(self):
        with patch.object(motor, "carregar_jurisprudencias", side_effect=AssertionError("não deve consultar")):
            a = motor.sugerir_assunto("Reduzir a multa contratual.")
            b = motor.sugerir_assunto("Não reduzir a multa contratual.")
        self.assertEqual(a["assunto"], b["assunto"])


class TestPreparacao(unittest.TestCase):
    def test_01_texto_curto_e_previa_completa(self):
        resultado = motor.preparar_documento(texto=TEXTO_MULTA)
        self.assertEqual(resultado["texto"], TEXTO_MULTA)
        self.assertEqual(resultado["previa"], TEXTO_MULTA)
        self.assertEqual(resultado["caracteres"], len(TEXTO_MULTA))
        self.assertFalse(resultado["previa_truncada"])

    def test_02_previa_limitada_sem_cortar_documento_ou_sugestao(self):
        texto = "x " * 2500 + "Cláusula penal."
        resultado = motor.preparar_documento(texto=texto)
        self.assertEqual(len(resultado["previa"]), motor.MAXIMO_PREVIA)
        self.assertTrue(resultado["previa_truncada"])
        self.assertEqual(resultado["texto"], texto)
        self.assertEqual(resultado["sugestao"]["assunto"], "Cláusula penal e multas")

    def test_03_hash_do_texto_efetivamente_lido(self):
        resultado = motor.preparar_documento(texto="  " + TEXTO_MULTA + "  ")
        self.assertEqual(resultado["documento_sha256"], sha256(TEXTO_MULTA.encode("utf-8")).hexdigest())

    def test_04_txt_utf8_e_latin1(self):
        for codificacao in ("utf-8-sig", "latin-1"):
            with self.subTest(codificacao=codificacao):
                resultado = motor.preparar_documento(arquivo=arquivo("teste.txt", TEXTO_MULTA.encode(codificacao)))
                self.assertEqual(resultado["texto"], TEXTO_MULTA)
                self.assertEqual(resultado["sugestao"]["assunto"], "Cláusula penal e multas")

    def test_05_docx_com_texto_apenas_na_tabela(self):
        doc = Document()
        doc.add_table(rows=1, cols=1).cell(0, 0).text = TEXTO_MULTA
        dados = io.BytesIO()
        doc.save(dados)
        resultado = motor.preparar_documento(arquivo=arquivo("tabela.docx", dados.getvalue()))
        self.assertIn(TEXTO_MULTA, resultado["texto"])
        self.assertEqual(resultado["sugestao"]["assunto"], "Cláusula penal e multas")

    def test_06_pdf_fragmentado_mantem_correcao(self):
        from test_pdf import pdf_fragmentado, TEXTO
        resultado = motor.preparar_documento(arquivo=arquivo("teste.pdf", pdf_fragmentado()))
        self.assertEqual(resultado["texto"].split(), TEXTO.split())
        self.assertEqual(resultado["sugestao"]["assunto"], "Cláusula penal e multas")

    def test_07_pdf_sem_texto_nao_ganha_assunto(self):
        pdf = PdfWriter()
        pdf.add_blank_page(width=200, height=200)
        dados = io.BytesIO()
        pdf.write(dados)
        resultado = motor.preparar_documento(arquivo=arquivo("vazio.pdf", dados.getvalue()))
        self.assertEqual(resultado["texto"], "")
        self.assertEqual(resultado["caracteres"], 0)
        self.assertEqual(resultado["sugestao"]["situacao"], "nao_identificado")

    def test_08_entradas_conflitantes_invalidas_e_limite(self):
        with self.assertRaises(ValueError):
            motor.preparar_documento(arquivo=arquivo("x.txt", b"x"), texto="texto")
        with self.assertRaises(ValueError):
            motor.preparar_documento(texto=None)
        with self.assertRaises(ValueError):
            motor.preparar_documento(texto="a" * (motor.MAXIMO_CARACTERES + 1))
        with self.assertRaises(ValueError):
            motor.preparar_documento(arquivo=arquivo("imagem.png", b"dados"))

    def test_09_nao_executa_analise_ou_conferencia(self):
        with patch.object(motor, "analisar_documento", side_effect=AssertionError("não analisar")), patch.object(motor, "conferir_referencias", side_effect=AssertionError("não conferir")):
            resultado = motor.preparar_documento(texto=TEXTO_MULTA)
        self.assertNotIn("resultados", resultado)
        self.assertNotIn("referencias", resultado)

    def test_10_documentos_distintos_nao_compartilham_preparacao(self):
        a = motor.preparar_documento(texto="Cláusula penal.")
        b = motor.preparar_documento(texto="Lucros cessantes.")
        self.assertNotEqual(a["documento_sha256"], b["documento_sha256"])
        self.assertNotEqual(a["sugestao"]["assunto"], b["sugestao"]["assunto"])
        self.assertEqual(a["texto"], "Cláusula penal.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
