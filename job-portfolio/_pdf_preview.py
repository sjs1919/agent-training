# -*- coding: utf-8 -*-
import fitz
f=r"E:\workspace\codebuddy_workspace\projects\agent-training\job-portfolio\简历-v4.4.A1.01-AI落地版.pdf"
doc=fitz.open(f)
for i,p in enumerate(doc):
    pix=p.get_pixmap(dpi=110)
    out=rf"E:\workspace\codebuddy_workspace\projects\agent-training\job-portfolio\_preview_p{i+1}.png"
    pix.save(out)
    print("saved", out, pix.width, "x", pix.height)
