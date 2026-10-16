import pypdfium2 as pdfium
import sys

def check(fname):
    pdf = pdfium.PdfDocument(fname)
    print(f"=== {fname} ({len(pdf)} pages) ===")
    for i in range(len(pdf)):
        txt = pdf[i].get_textpage().get_text_range()
        print(f"  Page {i+1}: {len(txt)} chars")
    print("  Last 200 chars of final page:")
    print("  " + repr(pdf[-1].get_textpage().get_text_range()[-200:]))

if __name__ == "__main__":
    fname = sys.argv[1] if len(sys.argv) > 1 else "GreenMind_AI_IEEE_5_Page.pdf"
    check(fname)
