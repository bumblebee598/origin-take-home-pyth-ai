import fitz
 
 
def prepare_paper(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n\n".join(page.get_text() for page in doc)
 
 
if __name__ == "__main__":
    import sys
    print(prepare_paper(sys.argv[1]))