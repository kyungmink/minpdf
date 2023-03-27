from io import BytesIO
from pikepdf import Pdf
from argparse import ArgumentParser

def main(sourcefile: str, page_list: list[str], destinationfile: str) -> None:
    """Pick pages into new pdf
    
    Appends to existing if desintation exists."""
    # Do not use context manager. Source streams must be open while writing
    # to destination stream. `dest_pdf` both source and destination if it
    # already exists. Therefore you need an intermediary that opens before the
    # sources close and closes after the destination opens, like a chain.
    try:
        dest_pdf = Pdf.open(destinationfile)
    except:
        dest_pdf = Pdf.new()
    # Do not close because reading page contents depends on open connection.
    # Open destination file to append to
    pdf = Pdf.open(sourcefile)
    # Parse pages
    for pagespec in page_list:
        if '-' in pagespec:
            bounds = [*map(int, pagespec.split('-'))]
            dest_pdf.pages.extend(pdf.pages[(bounds[0]-1):(bounds[1])])
        else:
            dest_pdf.pages.append(pdf.pages[int(pagespec)-1])
    with BytesIO() as buf:
        dest_pdf.save(buf)
        dest_pdf.close()
        pdf.close()
        buf.seek(0)
        with open(destinationfile, 'wb') as g:
            g.write(buf.read())


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('sourcefile')
    parser.add_argument('pages', help='comma separated pages and ranges of pages')
    parser.add_argument('destinationfile')
    args = parser.parse_args()
    page_list = args.pages.split(',')  # List of strings of form 1 or 1-2
    main(args.sourcefile, page_list, args.destinationfile)
