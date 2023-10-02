"""May reduce file size if image in pdf is not jpeg"""
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
      'source',
      help='Source pdf'
    )
    args = parser.parse_args()
    import pikepdf
    largepdf = pikepdf.Pdf.open(args.source)
    import itertools
    lrawimg = [*itertools.islice(largepdf.pages[0].images.values(), 0, 1)][0]
    lpdfimg = pikepdf.PdfImage(lrawimg)
    lpilimg = lpdfimg.as_pil_image()
    import PIL
    lpilimg = lpilimg.transpose(PIL.Image.Transpose.FLIP_TOP_BOTTOM)
    import io
    buf = io.BytesIO()
    lpilimg.save(buf, format="jpeg")
    buf.seek(0)
    import img2pdf
    with open("jpeg.pdf", "bw") as f:
        f.write(img2pdf.convert(buf))
