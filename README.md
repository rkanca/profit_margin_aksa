# Genset Price & Margin Calculator (Streamlit)

A simple web app for calculating selling prices and profit margins from a pricing Excel workbook (sheets: **GENSETS**, **FUEL TANKS**, **BREAKERS**) with branded PDF export.

## ✨ Features
- Upload Excel workbook
- Select genset by KW range, model, enclosure, engine S/N
- Optional fuel tank / breaker line items
- Margin slider & sales target input
- Downloadable **Profit Margin Summary** PDF with header:
  > Aksa Power Generation USA, Finance Department, Confidential

## 🔐 Password Protection
Set a password via Streamlit **Secrets** or an **environment variable**:

- **Streamlit Cloud** → App → *Settings* → *Secrets*:
  ```toml
  APP_PASSWORD = "1907"
