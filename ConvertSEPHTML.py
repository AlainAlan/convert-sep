import sys
import re
import requests
import pypandoc
import demjson
from string import Template
from bs4 import BeautifulSoup
from urlparse import urljoin

def heading_HTMLEntity2TeX(html_entity):
  heading_html = ''
  if html_entity.contents[0].name == 'a':
    heading_html = ''.join([unicode(e) for e in html_entity.contents[0].contents])
    heading_html = re.sub(r'^[0-9\. ]*', '', heading_html )
  else:
    heading_html = ''.join([unicode(e) for e in html_entity.contents])
    heading_html = re.sub(r'^[0-9\. ]*', '', heading_html )
  heading_TeX  = re.sub(r'\n', '', pypandoc.convert(heading_html, 'tex', format='html'))
  if(html_entity.name == 'h2'):
    heading_TeX = ''.join(['\\chapter{', heading_TeX, '}'])
  if(html_entity.name == 'h3'):
    heading_TeX = ''.join(['\\section{', heading_TeX, '}'])
  if(html_entity.name == 'h4'):
    heading_TeX = ''.join(['\\subsection{', heading_TeX, '}'])
  return heading_TeX

def paragraph_HTMLEntity2TeX(html_entity):
  paragraph_TeX = pypandoc.convert(unicode(html_entity), 'tex', format='html+tex_math_single_backslash')
  if re.search(r'\\textbackslash{}\(\\textbackslash\{\}ref\\{(.*)\\}\\textbackslash{}\)', paragraph_TeX):
    paragraph_TeX = re.sub(r'\\textbackslash{}\(\\textbackslash\{\}ref\\{(.*)\\}\\textbackslash{}\)', r'\\ref{\1}', paragraph_TeX)
  if re.search(r'\(\\textbackslash{}\((.*)\\textbackslash{}\)\)', paragraph_TeX):
    paragraph_TeX = re.sub(r'\(\\textbackslash{}\((.*)\\textbackslash{}\)\)', (lambda x: ''.join(['($', re.sub(r'\\textbackslash{}', r'\\', x.group(1)), '$)'])), paragraph_TeX)
  return paragraph_TeX

def blockquote_HTMLEntity2TeX(html_entity):
  return ''.join(['\\blockquote{', paragraph_HTMLEntity2TeX(html_entity),'}'])

def ul_HTMLEntity2TeX(html_entity):
  li_list = [''.join([unicode(e) for e in l.contents]) for l in html_entity.find_all('li')]
  li_list_TeX = [ ''.join(['\\item ', pypandoc.convert(l, 'tex', format='html+tex_math_single_backslash')]) for l in li_list ]
  return ''.join(['\\begin{itemize}\n', ''.join(li_list_TeX), '\n\\end{itemize}'])

def ol_HTMLEntity2TeX(html_entity):
  counter=''
  type=''
  if html_entity.has_attr('start'):
    counter = '\\setcounter{enumi}{' + str(int(html_entity['start']) - 1) + '}\n'
  if html_entity.has_attr('type'):
    type = ''.join(['[', html_entity['type'],']'])
  li_list = [''.join([unicode(e) for e in l.contents]) for l in html_entity.find_all('li')]
  li_list_TeX = [ ''.join(['\\item ', pypandoc.convert(l, 'tex', format='html+tex_math_single_backslash')]) for l in li_list ]
  return ''.join(['\\begin{enumerate}', type,'\n', counter, ''.join(li_list_TeX), '\n\\end{enumerate}'])

def ConvertHTMLElement(html_element, sidenote=False):
  tag = html_element.name
  if tag == 'h2' or tag == 'h3' or tag == 'h4':
    return heading_HTMLEntity2TeX(html_element)
  if tag == 'p' or tag == 'div' or tag == 'span':
    return paragraph_HTMLEntity2TeX(html_element)
  if tag == 'blockquote':
    if sidenote:
      return ''.join(['``', paragraph_HTMLEntity2TeX(html_element), '\'\'\\\\\\\\'])
    else:
      return blockquote_HTMLEntity2TeX(html_element)
  if tag == 'ul':
    return ul_HTMLEntity2TeX(html_element)
  if tag == 'ol':
    return ol_HTMLEntity2TeX(html_element)

def ConvertHTML(entry_html_entity):
  entry_TeX = ''
  if entry_html_entity:
    if entry_html_entity.children:
      for i in entry_html_entity.children:
        if i.name:
          entry_TeX = '\n'.join([entry_TeX, ConvertHTMLElement(i)])
        elif re.match(r'\\\[.*\\\]', str(i).strip(), re.DOTALL):
          entry_TeX = '\n'.join([entry_TeX, str(i).strip()])
  return entry_TeX

def OutputTeX(title, author, preamble='', main_text='', bibliography='', acknowledgments='', macros='', pubhistory='', copyright='', url=''):
  frontmatter_template=Template('\\documentclass[twoside]{tufte-book}\n\
\\usepackage{soul}\n\
\\usepackage{csquotes}\n\
\\usepackage{graphicx}\n\
\\usepackage{enumerate}\n\
\\usepackage{amsmath}\n\
\\usepackage{amssymb}\n\
\n\
\\usepackage{ifxetex}\n\
\\ifxetex\n\
  \\newcommand{\\textls}[2][5]{%\n\
    \\begingroup\\addfontfeatures{LetterSpace=#1}#2\\endgroup\n\
  }\n\
  \\renewcommand{\\allcapsspacing}[1]{\\textls[15]{#1}}\n\
  \\renewcommand{\\smallcapsspacing}[1]{\\textls[10]{#1}}\n\
  \\renewcommand{\\allcaps}[1]{\\textls[15]{\\MakeTextUppercase{#1}}}\n\
  \\renewcommand{\\smallcaps}[1]{\\smallcapsspacing{\\scshape\\MakeTextLowercase{#1}}}\n\
  \\renewcommand{\\textsc}[1]{\\smallcapsspacing{\\textsmallcaps{#1}}}\n\
  \\usepackage{fontspec}\n\
\\fi\n\
\\makeatletter\n\
\\newcommand{\\chapterauthor}[1]{%\n\
  {\\parindent0pt\\vspace*{-25pt}%\n\
  \linespread{1.1}\\large\scshape#1%\n\
  \par\\nobreak\\vspace*{35pt}}\n\
  \\@afterheading%\n\
}\n\
\\makeatother\n\
\n\
$macros\
\n\
\\title{$title}\n\
\\author{$author}\n\
\\begin{document}\n\
\\maketitle\n\
\\newpage\n\
~\\vfill\n\
\\thispagestyle{empty}\n\
\\setlength{\parindent}{0pt}\n\
\\setlength{\\parskip}{\\baselineskip}\n\
$copyright\n\
\n\
\par This is an article from \emph{Stanford Encyclopedia of Philosopy}, ed.~Edward N.~Zalta. URL: \\url{$url}\n\
\n\
\par $pubhistory\n\
\n\
% \par The script used to generate this file can be found at \\url{https://github.com/mondain-dev/ConvertSEP/}\n\
\\cleardoublepage\n')
  string_TeX = frontmatter_template.substitute(title=title, author=author, copyright=copyright, pubhistory=pubhistory, url=url, macros=macros)
  string_TeX = '\n'.join([string_TeX, preamble, '\n \\tableofcontents\n\n\\setcounter{secnumdepth}{2}',  main_text, bibliography, acknowledgments, '\\end{document}'])
  return string_TeX

def ProcessNotes(tex_src, base_url):
  note_list = re.findall(r'\\textsuperscript{{\[}\\href{(.*)\\#(.*)}{(.*)}{]}}', tex_src)
  soup_dict = {}
  for note_url in list(set([n[0] for n in note_list])):
    r = requests.get(urljoin(base_url, note_url))
    soup = BeautifulSoup(r.text)
    soup_dict[note_url] = soup
  
  for note_url in soup_dict:
    soup=soup_dict[note_url]
    note_num = None
    for i in soup.select('#aueditable')[0].children:
      if i.name:
        if i.name == 'div':
          if i.has_attr('id'):
            note_num = i['id']
        for a in i.find_all('a'):
          if a.has_attr('name'):
            note_num = a['name']
        if note_num:
          for j in xrange(len(note_list)):
            if note_list[j][1] == note_num and note_list[j][0] == note_url:
               if(len(note_list[j])==3):
                 note_list[j] = note_list[j] + ([],)
               note_list[j][3].append(i)
  
  for n in note_list:
    note_url = n[0]
    note_num = n[1]
    note_lab = n[2]
    for e in n[3]:
      for tag in e.find_all('a'):
        if tag.has_attr('name'):
          tag.replaceWith('')
    
    note_text = ''
    if len(n) > 3:
      note_text = '\n'.join([ConvertHTMLElement(e, True) for e in n[3]])
      note_text = ''.join(['\\sidenote[][]{', note_text, '}'])
    note_superscript = r'\\textsuperscript{{\[}\\href{'+ n[0] + r'\\#' + n[1] + r'}{'+ n[2] + r'.{\]}}'
    tex_src = re.sub(note_superscript, note_text, tex_src)
  
  return tex_src
    

def main():
  url=''
  output='output.tex'
  args = sys.argv[1:]
  if(len(args)>0):
    url = args[0]
    if( len(args)>1):
      output=args[1]
  else:
    helpConvertSEPHTML()
    sys.exit()
  
  r  = requests.get(url)
  
  soup = BeautifulSoup(r.text)
  
  TeXMacros = ''
  for s in soup.find_all('script'):
    if s.has_attr('src'):
      if s['src'] == 'local.js':
        r_TeXMacros = requests.get( urljoin(url, s['src']) )
        if re.search(r'window.MathJax\s*=\s*(.*);', r_TeXMacros.text, re.DOTALL):
          js_snippet  = re.search(r'window.MathJax\s*=\s*(.*);', r_TeXMacros.text, re.DOTALL).group(1)
          json_obj = demjson.decode(js_snippet)
          if 'TeX' in json_obj:
             if 'Macros' in json_obj['TeX']:
               for m in json_obj['TeX']['Macros']:
                 TeXMacros = '\n'.join([TeXMacros, ''.join(['\\newcommand{\\', m, '}{', json_obj['TeX']['Macros'][m], '}'])])
  
  title = soup.select('#aueditable h1')[0].text
  author_info = filter(None, [s.strip() for s in soup.select('#article-copyright')[0].text.split('by\n')[1].split('\n')])
  author = author_info[0]
  copyright_info = ' '.join(soup.select('#article-copyright')[0].text.split())
  pubhistory_info = soup.select('#pubinfo')[0].text
  preamble = soup.select('#aueditable #preamble')[0]
  main_text = soup.select('#aueditable #main-text')[0]
  bibliography = None
  if soup.select('#aueditable #bibliography'):
    bibliography = soup.select('#aueditable #bibliography')[0]
  acknowledgments = None
  if soup.select('#aueditable #acknowledgments'):
    acknowledgments = soup.select('#aueditable #acknowledgments')[0]
  
  preamble_TeX        = ConvertHTML(preamble)
  main_text_TeX       = ConvertHTML(main_text)
  bibliography_TeX    = ConvertHTML(bibliography)
  acknowledgments_TeX = ''
  if acknowledgments:
    if acknowledgments.children:
      for i in acknowledgments.children:
        if i.name:
          if i.name == "h3" and i.text == "Acknowledgments":
            acknowledgments_TeX = '\n'.join([acknowledgments_TeX, '\\setcounter{secnumdepth}{-1}\n\\chapter{Acknowledgments}'])
          else:
            acknowledgments_TeX = '\n'.join([acknowledgments_TeX, ConvertHTMLElement(i)])
  
  full_TeX   = OutputTeX(title, author, preamble_TeX, main_text_TeX, bibliography_TeX, acknowledgments_TeX, TeXMacros, pubhistory_info, copyright_info, url)
  full_TeX   = ProcessNotes(full_TeX, url)
  output_file = open(output, "w")
  output_file.write(full_TeX.encode('utf8'))
  output_file.close()

def helpConvertSEPHTML():
  args = sys.argv[0:]
  print(''.join(['Usage: \n', args[0], ' <URL to the entry> [<output.tex>] \n']))
  print(''.join(['For example:']))
  print(''.join(['\t', args[0], ' https://plato.stanford.edu/entries/comte/ comte.tex \n']))
  print(''.join(['or\n\t', args[0], ' https://plato.stanford.edu/entries/comte/ \n']))

if __name__ == "__main__":
  main()

