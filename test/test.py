from unittest import TestCase

class MyTestCase(TestCase):
    def test_pdfpick(self):
        from minpdf import pdfpick
        from pathlib import Path
        dest = Path(__file__).parent / "dest.pdf"
        dest.unlink(True)
        pdfpick.main(Path(__file__).parent / "test-facguide.pdf", ["0"], dest)
        pdfpick.main(Path(__file__).parent / "test-facguide.pdf", ["0"], dest)
        from pikepdf import Pdf
        pdf = Pdf.open(dest)
        self.assertEqual(pdf.pages[0], pdf.pages[1])

    def test_jpeg(self):
        from minpdf import jpeg
        from pathlib import Path
        jpeg.jpeg(Path(__file__).parent / "DC Medical license 2021.pdf")
