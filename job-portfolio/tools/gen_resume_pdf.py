# -*- coding: utf-8 -*-
"""
简历 MD → PDF 生成器
样式：深钢蓝商务风、留白优先、黑体标题+等线正文
用法：python gen_resume_pdf.py <input.md> <output.pdf>
"""
import sys
import re
from fpdf import FPDF

# ── 配色 ──
ACCENT  = (31, 78, 121)    # 深钢蓝（标题、强调）
DARK    = (26, 26, 26)     # 正文黑
GRAY    = (89, 89, 89)     # 次要文字
LIGHT   = (140, 140, 140)  # 更浅
HDR_BG  = (238, 242, 247)  # 标题栏浅蓝底
LINE_C  = (200, 208, 218)  # 分隔线

# ── 字体路径（Windows 自带）──
FONT_HEI  = r"C:/Windows/Fonts/simhei.ttf"   # 黑体
FONT_DENG = r"C:/Windows/Fonts/Deng.ttf"     # 等线
FONT_DENGB = r"C:/Windows/Fonts/Dengb.ttf"   # 等线粗体


class ResumePDF(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 16, 18)
        self.add_font("hei", "", FONT_HEI)
        self.add_font("deng", "", FONT_DENG)
        self.add_font("dengb", "", FONT_DENGB)
        self._in_bullet = False

    def header(self):
        pass  # 不需要页眉

    def footer(self):
        self.set_y(-12)
        self.set_font("deng", "", 8)
        self.set_text_color(*LIGHT)
        self.cell(0, 8, f"— {self.page_no()} —", align="C")

    # ── 渲染行内格式（粗体、代码）──
    def _inline(self, text, size=10, color=DARK):
        """解析 **粗体** 和 `代码`，逐段输出"""
        # 先按 ** 分割
        parts = re.split(r'(\*\*.*?\*\*|`.*?`)', text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                self.set_font("dengb", "", size)
                self.set_text_color(*ACCENT)
                self.write(5, part[2:-2])
            elif part.startswith("`") and part.endswith("`"):
                self.set_font("deng", "", size)
                self.set_text_color(*ACCENT)
                self.write(5, part[1:-1])
            else:
                self.set_font("deng", "", size)
                self.set_text_color(*color)
                self.write(5, part)
        self.ln(5)

    # ── 姓名大标题 ──
    def render_name(self, text):
        self.set_font("hei", "", 22)
        self.set_text_color(*ACCENT)
        self.cell(0, 12, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    # ── 副标题（岗位+信息行）──
    def render_subtitle(self, text):
        self.set_font("dengb", "", 11)
        self.set_text_color(*DARK)
        self.multi_cell(0, 6, text)
        self.ln(1)

    # ── 联系信息行 ──
    def render_contact(self, text):
        self.set_font("deng", "", 9.5)
        self.set_text_color(*GRAY)
        self.multi_cell(0, 5.5, text)
        # 画一条分隔线
        self.ln(1)
        self.set_draw_color(*LINE_C)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(3)

    # ── 关键词行 ──
    def render_keywords(self, text):
        # 去掉 > 前缀
        text = text.lstrip(">").strip()
        self.set_font("deng", "", 9.5)
        self.set_text_color(*ACCENT)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    # ── Pitch 引用块 ──
    def render_pitch(self, text):
        text = text.lstrip(">").strip()
        # 浅灰底块
        y_start = self.get_y()
        self.set_fill_color(*HDR_BG)
        self.set_x(18)
        # 先估算高度
        self.set_font("deng", "", 10.5)
        # 画左边竖线
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.8)
        # 输出内容
        self.set_x(22)
        self.set_text_color(*DARK)
        # 处理粗体
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                self.set_font("dengb", "", 10.5)
                self.set_text_color(*ACCENT)
                self.write(5.5, part[2:-2])
            else:
                self.set_font("deng", "", 10.5)
                self.set_text_color(*DARK)
                self.write(5.5, part)
        self.ln(5.5)
        y_end = self.get_y()
        # 画左边竖线
        self.line(19, y_start + 1, 19, y_end - 1)
        self.set_line_width(0.2)
        self.ln(3)

    # ── 一级章节标题（##）──
    def render_h2(self, text):
        # 去掉编号前缀如 "一、" "二、"
        self.ln(3)
        self.set_font("hei", "", 13)
        self.set_text_color(*ACCENT)
        # 标题前的小色块
        self.set_fill_color(*ACCENT)
        self.rect(18, self.get_y() + 1, 2.5, 5, style="F")
        self.set_x(23)
        self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    # ── 二级标题（###）──
    def render_h3(self, text):
        self.ln(2)
        self.set_font("hei", "", 11.5)
        self.set_text_color(*DARK)
        self.cell(0, 6.5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)

    # ── 三级标题（####）──
    def render_h4(self, text):
        self.ln(1)
        self.set_font("dengb", "", 10.5)
        self.set_text_color(*ACCENT)
        self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    # ── 列表项 ──
    def render_li(self, text, level=0):
        indent = 22 + level * 6
        self.set_x(indent)
        #  bullet 点
        self.set_font("deng", "", 10)
        self.set_text_color(*ACCENT)
        self.cell(4, 5.5, "•")
        self.set_x(indent + 4)
        # 内容（支持粗体）
        self._inline(text, size=10, color=DARK)

    # ── 普通段落 ──
    def render_p(self, text):
        self.set_x(18)
        self._inline(text, size=10, color=DARK)
        self.ln(1)

    # ── 分隔线 ──
    def render_hr(self):
        self.ln(1)
        self.set_draw_color(*LINE_C)
        self.set_line_width(0.2)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(2)


def parse_and_render(pdf, md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    first_h1 = True
    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()

        # 空行
        if not stripped:
            i += 1
            continue

        # 分隔线
        if stripped == "---":
            pdf.render_hr()
            i += 1
            continue

        # H1 — 姓名
        if stripped.startswith("# ") and not stripped.startswith("## "):
            text = stripped[2:].strip()
            if first_h1:
                pdf.render_name(text)
                first_h1 = False
            else:
                pdf.render_h2(text)
            i += 1
            continue

        # H2
        if stripped.startswith("## "):
            text = stripped[3:].strip()
            pdf.render_h2(text)
            i += 1
            continue

        # H3
        if stripped.startswith("### "):
            text = stripped[4:].strip()
            pdf.render_h3(text)
            i += 1
            continue

        # H4
        if stripped.startswith("#### "):
            text = stripped[5:].strip()
            pdf.render_h4(text)
            i += 1
            continue

        # 引用块（> 开头）
        if stripped.startswith(">"):
            # 合并连续的引用行
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            quote_text = " ".join(quote_lines)
            # 判断是关键词还是Pitch
            if "关键词" in quote_text or "｜" in quote_text and len(quote_text) < 80:
                pdf.render_keywords(quote_text)
            else:
                pdf.render_pitch(quote_text)
            continue

        # 无序列表
        if stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:].strip()
            # 检查缩进层级
            leading = len(line) - len(line.lstrip())
            level = leading // 2
            pdf.render_li(text, level)
            i += 1
            continue

        # 有序列表
        if re.match(r'^\d+\.\s', stripped):
            text = re.sub(r'^\d+\.\s*', '', stripped)
            pdf.render_li(text, 0)
            i += 1
            continue

        # 加粗的独立行（如 **业务背景**：...）
        if stripped.startswith("**") and "**" in stripped[2:]:
            pdf.render_p(stripped)
            i += 1
            continue

        # 普通段落（合并连续非空行）
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            next_line = lines[i].rstrip("\n")
            next_stripped = next_line.strip()
            if (not next_stripped or next_stripped.startswith("#") or
                next_stripped.startswith("- ") or next_stripped.startswith("* ") or
                next_stripped.startswith(">") or next_stripped == "---" or
                re.match(r'^\d+\.\s', next_stripped)):
                break
            para_lines.append(next_stripped)
            i += 1
        para_text = " ".join(para_lines)
        pdf.render_p(para_text)

    return pdf


def main():
    if len(sys.argv) < 3:
        print("用法: python gen_resume_pdf.py <input.md> <output.pdf>")
        sys.exit(1)

    input_md = sys.argv[1]
    output_pdf = sys.argv[2]

    pdf = ResumePDF()
    pdf.add_page()
    parse_and_render(pdf, input_md)
    pdf.output(output_pdf)
    print(f"✅ 生成成功: {output_pdf}")
    print(f"   页数: {pdf.page_no()}")


if __name__ == "__main__":
    main()
