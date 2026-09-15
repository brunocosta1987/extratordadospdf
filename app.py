import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
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
# UPLOAD DO PDF
# ============================================================

uploaded_pdf = st.file_uploader(
    "📄 Envie um arquivo PDF de recibos",
    type="pdf"
)


# ============================================================
# BOTÃO PARA INICIAR O PROCESSAMENTO
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

        # ========================================================
        # PROCESSAMENTO DO PDF
        # ========================================================

        with st.spinner("⏳ Processando os recibos..."):

            with pdfplumber.open(uploaded_pdf) as pdf:

                total_paginas = len(pdf.pages)

                for pagina_numero, page in enumerate(
                    pdf.pages,
                    start=1
                ):

                    text = page.extract_text()

                    if not text:
                        continue

                    # ------------------------------------------------
                    # Divide o conteúdo utilizando o início de cada
                    # "Recibo de Atendimento"
                    # ------------------------------------------------

                    blocos = re.split(
                        r"(?=Recibo de Atendimento\s*#)",
                        text,
                        flags=re.IGNORECASE
                    )

                    for bloco in blocos:

                        # Ignora partes que não sejam recibos
                        if not re.search(
                            r"Recibo de Atendimento\s*#",
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


                        # ====================================================
                        # 2. OBSERVAÇÕES
                        # ====================================================

                        observacoes_match = re.search(
                            r"Observações\s*(?:\r?\n|\r)\s*(.*?)"
                            r"\s*(?=\r?\n|\r)\s*Distância\b",
                            bloco,
                            flags=re.IGNORECASE | re.DOTALL
                        )


                        # ====================================================
                        # 3. DISTÂNCIA
                        # ====================================================

                        distancia_match = re.search(
                            r"Distância\s*(?:\r?\n|\r)\s*([\d.,]+)\s*km",
                            bloco,
                            flags=re.IGNORECASE
                        )


                        # ====================================================
                        # 4. TOTAL DO VOUCHER
                        # ====================================================

                        total_voucher_match = re.search(
                            r"Total\s+do\s+Voucher\s*"
                            r"(?:\r?\n|\r)\s*"
                            r"R\$\s*([\d.,]+)",
                            bloco,
                            flags=re.IGNORECASE
                        )


                        # ====================================================
                        # VERIFICA SE TODOS OS CAMPOS FORAM ENCONTRADOS
                        # ====================================================

                        if all([
                            recibo_match,
                            observacoes_match,
                            distancia_match,
                            total_voucher_match
                        ]):

                            numero_recibo = (
                                recibo_match
                                .group(1)
                                .strip()
                            )

                            observacoes = (
                                observacoes_match
                                .group(1)
                                .strip()
                            )

                            distancia = (
                                distancia_match
                                .group(1)
                                .strip()
                                .replace(".", "")
                                .replace(",", ".")
                            )

                            total_voucher = (
                                total_voucher_match
                                .group(1)
                                .strip()
                                .replace(".", "")
                                .replace(",", ".")
                            )


                            recibos.append({
                                "Recibo de Atendimento": numero_recibo,
                                "Total do Voucher (R$)": total_voucher,
                                "Distância (km)": distancia,
                                "Observações": observacoes
                            })


        # ========================================================
        # RESULTADOS
        # ========================================================

        if recibos:

            df = pd.DataFrame(recibos)

            st.success(
                f"✅ {len(df)} recibos extraídos com sucesso!"
            )

            st.dataframe(
                df,
                use_container_width=True
            )


            # ====================================================
            # GERAR EXCEL
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

            st.warning(
                "⚠️ Nenhum recibo foi identificado no PDF enviado. "
                "Verifique se o documento está no formato esperado."
            )
