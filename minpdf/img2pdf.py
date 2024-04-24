import argparse
import img2pdf
from PIL import Image
import pathlib
from time import time
from re import compile
from os import remove, path, scandir
from os.path import exists, splitext
from io import BytesIO
from pikepdf import Pdf

__all__ = [
  "upload_clean", "to_letter_ratio", "to_realsize_pdf", "chain_pdfs"
]

def upload_clean():
  '''Purely for Google Colab'''
  start = time()
  uploaded = files.upload()
  # files.upload renames files if exists. To overwrite I do the following:
  # Remove files by the pattern "name (1)" if they were created after start.
  for key, content in uploaded.items():
    with open(key, 'wb') as f:
      f.write(content)
    pattern = compile(path.splitext(key)[0] + r' \(\d+\)')
    with scandir() as entries:
      for entry in entries:
        if pattern.match(entry.name) and entry.stat().st_mtime > start:
          remove(entry)
  return list(uploaded.keys())

def to_letter_ratio(imgfile, *, out:str='temporary.jpg', dpi:int=600, save_bytes_factor:int=1)->str:
  with Image.open(imgfile) as img:
    if img.width > 8.5 * dpi: 
      print("Trimming width.")
      img = img.crop((0,0, 8.5 * dpi,img.height))
    if img.height > 11 * dpi:
      print("Trimming height.")
      img = img.crop((0, 0, img.width, 11 * dpi))
    img = img.reduce(save_bytes_factor)
    nameparts = splitext(imgfile)
    img.save(out)
    return out

def to_realsize_pdf(imgfile, dpi:int=150, save_bytes_factor:int=1):
    '''Converts to letter-sized pdf pages.
    
    :returns: new pdf filename.'''
    # to_letter_ratio returns a file path string.
    newFile = to_letter_ratio(imgfile, dpi=dpi, save_bytes_factor=save_bytes_factor)
    dpi = dpi / save_bytes_factor
    pdfdata = img2pdf.convert([newFile])
    pdf = Pdf.open(BytesIO(pdfdata))
    remove(newFile)
    page = pdf.pages[0]
    # Define page. The PDF default resolution is 72 points per inch, and the
    # U.S. letter size (8.5 x 11 in.) is 612 x 792 points.
    page.mediabox = [0, 0, int(612), int(792)]
    from pikepdf import parse_content_stream, PdfMatrix, PdfImage, Array, unparse_content_stream
    rawimage = page.images['/Im0']  # The raw object/dictionary
    pdfimage = PdfImage(rawimage)
    commands = [[operands, operator] for operands, operator 
              in parse_content_stream(page)]
    original = PdfMatrix(commands[1][0])
    # Calculate the transformation required to center the image on the page
    # and scale it according to specified original physical resolution.
    # Then apply the transformation by postmultiplication (i.e., after)
    # the transformation already applied by img2pdf.
    # img2pdf applies a transformation that treats the image like a 96
    # pixel-per-inch image. Specifically, it maps 96 pixels to 72 points in
    # the PDF. The use of the term "points" is confusing because it is a
    # measure of distance and not a measure of information in the PDF space (
    # one point has 4/3 pixels mapped onto it). Henceforth I will use the term
    # "unit" to refer to a "point" in the default PDF space to avoid this
    # confusion. img2pdf maps 96 pixels to a distance of 72 units. To center
    # an image onto a physical medium (in this case the U.S. letter paper), it
    # it can be translated either before or after scaling. It is simple to
    # center it in its native resolution (pixels per inch). If the native
    # resolution is r and its pixel dimension is w then to center it in a
    # space of w' it must be translated by (rw' - w)/2 pixels. Any subsequent
    # scaling preserves the origin (0, 0) of the axis/axes, which is the
    # corner of the medium. After the scaling operation by img2pdf (by a
    # factor of 3/4), the equivalent translation should be also scaled.
    # Therefore it should be (rw' - w) / 2 * (3/4). Substituting 8.5 (in.) for
    # w' and refactoring it to keep computations in the numerator in the
    # integer group/space, gives (51r - 6w) / 16 for the horizontal axis.
    # Subsequent scaling to map r pixels in the original image to 72 units
    # must squish r pixels into the 72-unit space into which img2pdf had
    # squished 96 pixels. The scaling factor therefore equals 96/r.
    #
    # Apply the translation and scaling transformations using the solution
    # above. Compute the resulting CTM.
    new_matrix     = original    .translated(
          (51 * dpi - pdfimage.width * 6) / 16
        , (66 * dpi - pdfimage.height * 6) / 16
    )\
    .scaled(96 / dpi, 96 / dpi)
    # Substitute the CTM into the PDF.
    commands[1][0] = Array([*new_matrix.shorthand])
    new_content_stream = unparse_content_stream(commands)
    page.Contents = pdf.make_stream(new_content_stream)
    new = splitext(imgfile)[0] + '.pdf'
    if exists(new):
        raise IOError(f"Destination file '{new}' exists.")
    pdf.save(new)
    return new

def chain_pdfs(stem: str):
    '''Chains single-page PDFs into one multi-page PDF.
    
    :param stem: Stem used to search file names to aggregate.
     
    For example,
    'stem'='Scan_20221205' will collect 'Scan_20221205.pdf', 'Scan_20221205 (2).pdf,'
    etc.'''
    try:
        remove('n.pdf')
    except FileNotFoundError:
        pass
    pat = compile(f'{stem}(.*).pdf')
    def keyfunc(path):
        match = pat.match(str(path)).group(1).strip(' ()')
        return int(match) if match else 0
    pdf_o = None
    for i, path in enumerate(sorted(pathlib.Path().glob(f'{stem}*.pdf'), key=keyfunc)):
        if pdf_o is not None:
            pdf_a = Pdf.open(path)
            try:
                pdf_o.pages.remove(p=i+1)
            except IndexError:
                pass
            pdf_o.pages.insert(i, pdf_a.pages[0])
        else:
            pdf_o = Pdf.open(path)
    if pdf_o is None:
        raise FileNotFoundError
    else:
        pdf_o.save('n.pdf')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
      'stem',
      help='If your image is named "Scan.jpg" just put "Scan".'
    )
    parser.add_argument(
      '-d', '--dpi', type=int, default=300,
      help='DPI (dots per inch) of the source image.'
    )
    args = parser.parse_args()
    for path in pathlib.Path().glob(f'{args.stem}*.jpg'):
        to_realsize_pdf(path, dpi=args.dpi, save_bytes_factor=1)
    chain_pdfs(args.stem)
