# -*- coding: utf-8 -*-
"""用本机 Word (COM) 把 docx 转成 PDF。需要 Microsoft Word 已安装。"""
import os, sys
import win32com.client

BASE = r"E:\workspace\codebuddy_workspace\projects\agent-training\job-portfolio"
docx_path = os.path.join(BASE, "简历-v4.4.A1.01-AI落地版.docx")
pdf_path  = os.path.join(BASE, "简历-v4.4.A1.01-AI落地版.pdf")

if not os.path.exists(docx_path):
    print("DOCX NOT FOUND:", docx_path); sys.exit(1)

wd = win32com.client.Dispatch("Word.Application")
wd.Visible = False
try:
    doc = wd.Documents.Open(docx_path)
    doc.SaveAs(pdf_path, FileFormat=17)  # 17 = wdFormatPDF
    doc.Close()
    print("PDF SAVED:", pdf_path, os.path.getsize(pdf_path), "bytes")
finally:
    wd.Quit()
