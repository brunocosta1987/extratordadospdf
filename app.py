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
    "para extrair as informações estruturadas em Excel."
)


# ============================================================
# UPLOAD DO PDF
# ============================================================

uploaded_pdf = st.file_uploader(
    "📄 Envie um arquivo PDF de recibos",
    type="pdf"
)


# ============================================================
# PROCESSAMENTO DO PDF
# ============================================================

if uploaded_pdf is not None:

    recibos = []

    with pdfplumber.open(uploaded_pdf) as pdf:

        for page in pdf.pages:

            text = page.extract_text()

            if not text:
                continue

            # ------------------------------------------------
            # O novo modelo possui um recibo por página.
            # Entretanto, mantemos a divisão por "Recibo de
            # Atendimento" para permitir mais de um recibo
            # caso isso ocorra em algum PDF.
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
                #
                # Exemplo:
                # Recibo de Atendimento #664479
                #
                # Captura somente o número depois do símbolo #.
                # ====================================================

                recibo_match = re.search(
                    r"Recibo\s+de\s+Atendimento\s*#\s*(\d+)",
                    bloco,
                    flags=re.IGNORECASE
                )


                # ====================================================
                # 2. OBSERVAÇÕES
                # ====================================================
                #
                # Exemplo:
                #
                # Observações
                # RETORNO DE COLABORADOR
                # Distância
                #
                # O programa captura somente o conteúdo entre
                # "Observações" e "Distância".
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
                #
                # Exemplo:
                #
                # Distância
                # 55 km
                #
                # ====================================================

                distancia_match = re.search(
                    r"Distância\s*(?:\r?\n|\r)\s*([\d.,]+)\s*km",
                    bloco,
                    flags=re.IGNORECASE
                )


                # ====================================================
                # 4. TOTAL DO VOUCHER
                # ====================================================
                #
                # Exemplo:
                #
                # Total do Voucher
                # R$ 225,50
                #
                # IMPORTANTE:
                # Não procuramos simplesmente "R$".
                #
                # Procuramos especificamente o valor associado
                # ao campo "Total do Voucher", evitando confundir
                # com "Valor da Corrida".
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

                    numero_recibo = recibo_match.group(1).strip()

                    observacoes = observacoes_match.group(1).strip()

                    distancia = (
                        distancia_match.group(1)
                        .strip()
                        .replace(".", "")
                        .replace(",", ".")
                    )

                    total_voucher = (
                        total_voucher_match.group(1)
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


    # ============================================================
    # EXIBIÇÃO DOS RESULTADOS
    # ============================================================

    if recibos:

        df = pd.DataFrame(recibos)

        st.success(
            f"✅ {len(df)} recibos extraídos com sucesso!"
        )

        st.dataframe(
            df,
            use_container_width=True
        )


        # ========================================================
        # GERAR EXCEL
        # ========================================================

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
            )
        )


    else:

        st.warning(
            "⚠️ Nenhum recibo foi identificado no PDF enviado. "
            "Verifique se o documento está no formato esperado."
        )
