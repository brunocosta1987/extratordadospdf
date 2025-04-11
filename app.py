import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Extrator de Recibos eletrônico de Táxi para Excel", layout="centered")
st.title("📥 Extrator de Recibos eletrônico de Táxi para Excel")
st.write("Envie um arquivo PDF com os recibos eletrônicos de táxi para extrair as informações estruturadas em Excel.")

# Upload do PDF
uploaded_pdf = st.file_uploader("📄 Envie o arquivo PDF de recibos", type="pdf")

if uploaded_pdf is not None:
    recibos = []
    with pdfplumber.open(uploaded_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            blocos = text.split("Recibo Eletrônico de Táxi")
            for bloco in blocos:
                voucher_match = re.search(r"Voucher:\s*#(\d+)", bloco)
                valor_match = re.search(r"R\$ ?([\d.,]+)", bloco)
                distancia_match = re.search(r"Distância:\s*([\d.,]+)\s*km", bloco)
                protocolo_match = re.search(r"Protocolo MPRJ:\s*(.*?)\n", bloco)

                if all([voucher_match, valor_match, distancia_match, protocolo_match]):
                    recibos.append({
                        "Número do Voucher": voucher_match.group(1).strip(),
                        "Valor do Recibo (R$)": valor_match.group(1).replace(",", "."),
                        "Distância (km)": distancia_match.group(1).replace(",", "."),
                        "Protocolo MPRJ": protocolo_match.group(1).strip()
                    })

    if recibos:
        df = pd.DataFrame(recibos)
        st.success(f"✅ {len(df)} recibos extraídos com sucesso!")
        st.dataframe(df)

        # Gerar Excel para download
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button("⬇️ Baixar Excel", data=output.getvalue(), file_name="recibos_mprj.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.warning("Nenhum recibo foi identificado no PDF enviado. Verifique o formato do documento.")
