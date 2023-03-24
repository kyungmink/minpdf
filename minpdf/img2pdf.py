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
    newFile = to_letter_ratio(imgfile, dpi=dpi, save_bytes_factor=save_bytes_factor)
    dpi = dpi / save_bytes_factor
    pdfdata = img2pdf.convert([newFile])
    pdf = Pdf.open(BytesIO(pdfdata))
    remove(newFile)
    page = pdf.pages[0]
    page.mediabox = [0, 0, int(612), int(792)]
    from pikepdf import parse_content_stream, PdfMatrix, PdfImage, Array, unparse_content_stream
    rawimage = page.images['/Im0']  # The raw object/dictionary
    pdfimage = PdfImage(rawimage)
    commands = [[operands, operator] for operands, operator 
              in parse_content_stream(page)]
    original = PdfMatrix(commands[1][0])
    new_matrix     = original    .translated(
          (51 * dpi - pdfimage.width * 6) / 16
        , (66 * dpi - pdfimage.height * 6) / 16
    )\
    .scaled(96 / dpi, 96 / dpi)
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
    
    :param stem: Stem used to search file names to aggregate. For example,
    'Scan_20221205' will collect 'Scan_20221205.pdf', 'Scan_20221205 (2).pdf,'
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
    parser.add_argument('stem')
    parser.add_argument(
      '-d', '--dpi', type=int, default=300,
      help='DPI (dots per inch) of the source image.'
    )
    args = parser.parse_args()
    for path in pathlib.Path().glob(f'{args.stem}*.jpg'):
        to_realsize_pdf(path, dpi=args.dpi, save_bytes_factor=1)
    chain_pdfs(args.stem)

# pdfdata = img2pdf.convert(*[str(path) for path in pathlib.Path('.').glob('20221205*.jpg')])
# with open('n.pdf', 'wb') as f:
#     f.write(pdfdata)
