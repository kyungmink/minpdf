"""May reduce file size if image in pdf is not jpeg

Extracts first image resource from the first page only."""
def jpeg(source: str) -> None:
    import pikepdf
    largepdf = pikepdf.Pdf.open(source)
    # Extract first image from first page
    import itertools
    page = largepdf.pages[0]
    lrawimg = [*itertools.islice(page.images.values(), 0, 1)][0]
    lpdfimg = pikepdf.PdfImage(lrawimg)
    lpilimg = lpdfimg.as_pil_image()
    # Save image in jpeg format to a buffer.
    import io
    buf = io.BytesIO()
    lpilimg.save(buf, format="jpeg")
    # Track axis flips.
    # The reason for using 306 and 396 is that the default PDF user space
    # resolution is 72 points-per-inch. The U.S. letter is therefore 612 x 792
    # The orientation can be tracked using the fact that orientation is
    # (-1)^n where n is the number of inversions.
    # Then the scaling factor for the x axis should be (2 x 306) x (-1)^n and
    # and translation should be 306 - 306 x (-1)^n . This results in a scaling
    # factor of 612 and translation of 0 if the x axis is not reversed, and a
    # scaling factor of -612 and a translation of 612 if the x axis is
    # reversed. The y axis works similarly.
    # Calculate the common terms 306 x (-1)^n and 396 x (-1)^n for the x and
    # y axes, respectively.
    x_or_term, y_or_term = (306, 396)
    for operand, operator in pikepdf.parse_content_stream(page):
        print(*operand)
        if str(operator) == "cm":
            x_or_term *= 1 if operand[0] >= 0 else -1
            y_or_term *= 1 if operand[3] >= 0 else -1
    # Rewind buffer to read from the beginning
    buf.seek(0)
    import img2pdf
    # Wrap pdfdata in BytesIO and create new pdf from it.
    newpdf = pikepdf.open(io.BytesIO(img2pdf.convert(buf)))
    # The structure of img2pdf's output content stream is predictable.
    # The first command pushes a stack with the operator "q".
    # The second command appends the CTM (current transformation matrix) with the
    # operator "cm".
    # The third command draws the image with the operator "Do".
    # The fourth (last) command pops the stack with the operator "Q".
    # More information about these commands and CTM can be obtained from the
    # the
    # [PDF standard definition](https://opensource.adobe.com/\
    # dc-acrobat-sdk-docs/pdfstandards/pdfreference1.0.pdf).
    commands = [[operator, operand] for operator, operand
                in pikepdf.parse_content_stream(newpdf.pages[0])]
    # Rewrite operand in second command
    commands[1][0] = pikepdf.Array([
        2 * x_or_term, 0, 0, 2 * y_or_term,
        306 - x_or_term, 396 - y_or_term
    ])
    # In the above, the 6-dimensional operand [a, b, c, d, e, f] sets a
    # CTM in which coordinate X = [x, y] will be transformed to
    # XM + T where M is the 2 x 2 matrix [[a, b], [c, d]] and T is the 1 x 2
    # matrix [e, f]. For example, [612, 0, 0, 792, 0, 0] will scale a unit
    # square by 612 along the x axis and 792 along the y axis. A x_orientation
    # value of -1 will flip the square along the x axis, and likewise for the
    # y_orientation. The next and third command draws the image into a unit
    # square; the fourth command pops the stack, at which time the CTM is
    # is applied. This results in the image being placed over 612 x 792
    # points. Finallym the image fills a U.S. letter page (8.5 x 11 in.) at 72
    # dpi.
    #
    # Output new pdf.
    newpdf.pages[0].Contents = newpdf.make_stream(
        pikepdf.unparse_content_stream(commands)
    )
    newpdf.pages[0].mediabox = [0, 0, 612, 792]
    newpdf.save("jpeg.pdf")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
      'source',
      help='Source pdf'
    )
    args = parser.parse_args()
    jpeg(args.source)
    