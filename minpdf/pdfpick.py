from pikepdf import Pdf
from argparse import ArgumentParser

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('sourcefile')
    parser.add_argument('pages', help='comma separated pages and ranges of pages')
    parser.add_argument('destinationfile')
    args = parser.parse_args()
    page_list = args.pages.split(',')
    f = open(args.sourcefile, 'rb')
    pdf = Pdf.open(f)
    pages = []
    for pagespec in page_list:
        if '-' in pagespec:
            bounds = [*map(int, pagespec.split('-'))]
            pages.extend(pdf.pages[(bounds[0]-1):(bounds[1])])
        else:
            pages.append(pdf.pages[pagespec-1])
    pdf.pages[:] = pages
    with open(args.destinationfile, 'wb') as g:
        pdf.save(g)
    f.close()
