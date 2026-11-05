from pypdf import PdfReader


def load_pdf(path):

    reader = PdfReader(path)

    text = ""

    for page in reader.pages:
        text += page.extract_text()

    return text


if __name__ == "__main__":
    result = load_pdf("data/documents/scheme.pdf")

    print(result[:1000])
