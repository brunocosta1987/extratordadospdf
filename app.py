import streamlit as st
import pdfplumber
import pandas as pd
import re
import unicodedata
from io import BytesIO

# OCR
from rapidocr_onnxruntime import RapidOCR


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Extrator de Recibos Eletrônicos de Táxi para Excel",
    layout="centered"
)

st.title("📥 Extrator de Recibos Eletrônicos de Táxi para Excel")

st.write(
    "Envie um arquivo PDF com os recibos eletrônicos de táxi "
    "e clique em **Iniciar extração** para processar o documento."
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalizar_texto(texto):
    """
    Remove acentos e normaliza espaços para facilitar
    a identificação dos campos pelo OCR.
    """
    if not texto:
        return ""

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )

    texto = texto.replace("\r", "\n")

    # Remove espaços duplicados
    texto = re.sub(r"[ \t]+", " ", texto)

    # Remove linhas vazias duplicadas
    texto = re.sub(r"\n\s*\n+", "\n", texto)

    return texto.strip()


def limpar_numero_brasileiro(valor):
    """
    Converte:
    1.234,56 -> 1234.56
    55,50    -> 55.50
    55       -> 55
    """
    if not valor:
        return ""

    valor = valor.strip()

    if "," in valor:
        valor = valor.replace(".", "")
        valor = valor.replace(",", ".")
    else:
        # Mantém números sem separador decimal
        valor = valor.replace(",", ".")

    return valor


def extrair_com_ocr(page, ocr):
    """
    Converte a página do PDF em imagem e executa OCR.
    """

    imagem = page.to_image(
        resolution=250
    ).original

    resultado, _ = ocr(imagem)

    if not resultado:
        return ""

    linhas = []

    for item in resultado:

        # RapidOCR retorna:
        # [caixa, texto, confiança]
        if len(item) >= 2:
            texto = item[1]

            if texto:
                linhas.append(str(texto))

    return "\n".join(linhas)


def extrair_recibos_do_texto(text):
    """
    Extrai os dados de um ou mais recibos.
    """

    recibos = []

    if not text:
        return recibos

    # ========================================================
    # Normalização
    # ========================================================

    texto_original = text

    texto = normalizar_texto(texto_original)

    # ========================================================
    # Localiza cada Recibo de Atendimento
    # ========================================================

    blocos = re.split(
        r"(?=Recibo\s+de\s+Atendimento\s*#)",
        texto,
        flags=re.IGNORECASE
    )

    for bloco in blocos:

        if not re.search(
            r"Recibo\s+de\s+Atendimento\s*#",
            bloco,
            flags=re.IGNORECASE
        ):
            continue

        # ====================================================
        # 1. RECIBO DE ATENDIMENTO
        # ====================================================

        recibo_match = re.search(
            r"Recibo\s+de\s+Atendimento\s*#\s*(\d+)",
            bloco,
            flags=re.IGNORECASE
        )

        if not recibo_match:
            continue

        numero_recibo = recibo_match.group(1).strip()


        # ====================================================
        # 2. DISTÂNCIA
        # ====================================================

        distancia_match = re.search(
            r"Dist[aâ]ncia\b"
            r".{0,100}?"
            r"(\d+(?:[.,]\d+)?)\s*km",
            bloco,
            flags=re.IGNORECASE | re.DOTALL
        )

        if distancia_match:
            distancia = limpar_numero_brasileiro(
                distancia_match.group(1)
            )
        else:
            distancia = ""


        # ====================================================
        # 3. TOTAL DO VOUCHER
        # ====================================================

        total_voucher_match = re.search(
            r"Total\s+do\s+Voucher\b"
            r".{0,150}?"
            r"R\$\s*([\d.,]+)",
            bloco,
            flags=re.IGNORECASE | re.DOTALL
        )

        if total_voucher_match:
            total_voucher = limpar_numero_brasileiro(
                total_voucher_match.group(1)
            )
        else:
            total_voucher = ""


        # ====================================================
        # 4. OBSERVAÇÕES
        # ====================================================
        #
        # O campo pode estar:
        #
        # Observações
        # RETORNO DE COLABORADOR
        #
        # ou pode estar vazio.
        #
        # Portanto, não vamos considerar a ausência de
        # observação como motivo para descartar o recibo.
        # ====================================================

        observacoes = ""

        observacoes_match = re.search(
            r"Observa[cç][oõ]es\b\s*(.*?)"
            r"(?=\b(?:RETORNO\s+DE\s+COLABORADOR|"
            r"RESUMO\s+FINANCEIRO|Dist[aâ]ncia\b|"
            r"TOTAL\s+DO\s+VOUCHER\b))",
            bloco,
            flags=re.IGNORECASE | re.DOTALL
        )

        if observacoes_match:

            observacoes = (
                observacoes_match
                .group(1)
                .strip()
            )

            # Remove textos que eventualmente tenham sido
            # capturados junto com o campo.
            observacoes = re.sub(
                r"\s+",
                " ",
                observacoes
            ).strip()


        # ====================================================
        # CASO ESPECIAL:
        # Se "Observações" estiver imediatamente antes de
        # "RETORNO DE COLABORADOR", captura o texto.
        # ====================================================

        retorno_match = re.search(
            r"Observa[cç][oõ]es\b\s*"
            r"(RETORNO\s+DE\s+COLABORADOR)",
            bloco,
            flags=re.IGNORECASE
        )

        if retorno_match:
            observacoes = retorno_match.group(1).strip()


        # ====================================================
        # ADICIONA O RECIBO
        # ====================================================

        recibos.append({
            "Recibo de Atendimento": numero_recibo,
            "Total do Voucher (R$)": total_voucher,
            "Distância (km)": distancia,
            "Observações": observacoes
        })

    return recibos


# ============================================================
# UPLOAD
# ============================================================

uploaded_pdf = st.file_uploader(
    "📄 Envie um arquivo PDF de recibos",
    type="pdf"
)


# ============================================================
# BOTÃO DE PROCESSAMENTO
# ============================================================

if uploaded_pdf is not None:

    st.success(
        f"📄 Arquivo carregado: **{uploaded_pdf.name}**"
    )

    iniciar_extracao = st.button(
        "🔍 Iniciar extração",
        type="primary",
        use_container_width=True
    )

    if iniciar_extracao:

        recibos = []

        # ====================================================
        # INICIALIZA OCR
        # ====================================================

        ocr = RapidOCR()

        progresso = st.progress(0)

        status = st.empty()

        # ====================================================
        # ABRE PDF
        # ====================================================

        with st.spinner("⏳ Processando o PDF..."):

            with pdfplumber.open(uploaded_pdf) as pdf:

                total_paginas = len(pdf.pages)

                for pagina_numero, page in enumerate(
                    pdf.pages,
                    start=1
                ):

                    status.write(
                        f"📄 Processando página "
                        f"{pagina_numero} de {total_paginas}..."
                    )

                    # ====================================================
                    # PRIMEIRA TENTATIVA:
                    # EXTRAÇÃO NORMAL DO PDF
                    # ====================================================

                    text = page.extract_text()


                    # ====================================================
                    # SEGUNDA TENTATIVA:
                    # OCR
                    #
                    # Se o PDF for imagem, extract_text() retorna vazio.
                    # Nesse caso, fazemos OCR automaticamente.
                    # ====================================================

                    if not text or len(text.strip()) < 20:

                        status.write(
                            f"🔎 Página {pagina_numero}: "
                            f"texto não encontrado. Executando OCR..."
                        )

                        text = extrair_com_ocr(
                            page,
                            ocr
                        )


                    # ====================================================
                    # EXTRAÇÃO DOS DADOS
                    # ====================================================

                    if text:

                        encontrados = (
                            extrair_recibos_do_texto(text)
                        )

                        recibos.extend(encontrados)


                    # Atualiza progresso
                    progresso.progress(
                        pagina_numero / total_paginas
                    )


        status.empty()
        progresso.empty()


        # ====================================================
        # RESULTADOS
        # ====================================================

        if recibos:

            # ------------------------------------------------
            # Remove possíveis duplicidades
            # ------------------------------------------------

            df = pd.DataFrame(recibos)

            df = df.drop_duplicates(
                subset=["Recibo de Atendimento"],
                keep="first"
            )

            # ------------------------------------------------
            # Quantidade final
            # ------------------------------------------------

            quantidade = len(df)

            st.success(
                f"✅ {quantidade} recibo(s) extraído(s) com sucesso!"
            )


            # ------------------------------------------------
            # TABELA
            # ------------------------------------------------

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )


            # ====================================================
            # GERA EXCEL
            # ====================================================

            output = BytesIO()

            df.to_excel(
                output,
                index=False
            )

            output.seek(0)


            st.download_button(
                label="⬇️ Baixar Excel",
                data=output.getvalue(),
                file_name="recibos_mprj.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True
            )


        else:

            st.error(
                "⚠️ Nenhum recibo foi identificado no PDF."
            )

            st.info(
                "O programa tentou primeiro fazer a leitura "
                "direta do PDF e, depois, utilizar OCR. "
                "Verifique se o arquivo contém recibos no "
                "modelo esperado."
            )
